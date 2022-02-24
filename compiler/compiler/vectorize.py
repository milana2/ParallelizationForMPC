from collections import defaultdict

from .ast_shared import TypeEnv, Var, VectorizedAccess, Subscript
from .tac_cfg import DropDim, LiftExpr, Assign
from . import loop_linear_code as llc
from .dep_graph import DepGraph, DepNode, EdgeKind
from . import util
from .util import assert_never

import dataclasses as dc
from dataclasses import dataclass
from typing import Iterable, Union, Optional, cast

import z3  # type: ignore


@dataclass
class ArrayRead:
    subscript: llc.Subscript
    parent_loops: list[llc.For]


class TempVarGenerator:
    _max_temp_var_num: int

    def __init__(self, dep_graph: DepGraph) -> None:
        nodes: Iterable[DepNode] = dep_graph.def_use_graph.nodes
        self._max_temp_var_num = max(
            [
                0 if isinstance(a.lhs.name, str) else a.lhs.name
                for a in nodes
                # Skip vectorized assignments since every variable will be initially assigned
                if not isinstance(a.lhs, VectorizedAccess)
            ]
        )

    def get(self) -> llc.Var:
        self._max_temp_var_num += 1
        return llc.Var(self._max_temp_var_num, 0)


def _arrays_written_in_loop(loop: llc.For) -> list[llc.Assign]:
    """
    Return the list of array updates inside the loop, including nested loops.
    """
    result: list[llc.Assign] = []
    for statement in loop.body:
        if isinstance(statement, llc.Phi):
            pass
        elif isinstance(statement, llc.Assign):
            if isinstance(statement.rhs, llc.Update):
                result.append(statement)
        elif isinstance(statement, llc.For):
            result += _arrays_written_in_loop(statement)
        else:
            assert_never(statement)
    return result


def _arrays_read_in_rhs(
    rhs: llc.AssignRHS, array_name: Union[str, int]
) -> list[llc.Subscript]:
    # TODO: is it correct to ignore LiftExpr, DropDim, and VectorizedArr?
    if isinstance(rhs, (llc.Var, llc.Constant, LiftExpr, DropDim, VectorizedAccess)):
        return []
    elif isinstance(rhs, llc.Subscript):
        if rhs.array.name == array_name:
            return [rhs]
        else:
            return []
    elif isinstance(rhs, llc.BinOp):
        left = _arrays_read_in_rhs(rhs.left, array_name)
        right = _arrays_read_in_rhs(rhs.right, array_name)
        return left + right
    elif isinstance(rhs, llc.UnaryOp):
        return _arrays_read_in_rhs(rhs.operand, array_name)
    elif isinstance(rhs, (llc.List, llc.Tuple)):
        return [
            subscript
            for item in rhs.items
            for subscript in _arrays_read_in_rhs(item, array_name)
        ]
    elif isinstance(rhs, llc.Mux):
        return (
            _arrays_read_in_rhs(rhs.condition, array_name)
            + _arrays_read_in_rhs(rhs.false_value, array_name)
            + _arrays_read_in_rhs(rhs.true_value, array_name)
        )
    elif isinstance(rhs, llc.Update):
        return _arrays_read_in_rhs(rhs.value, array_name)
    else:
        assert_never(rhs)


def _arrays_read_in_loop(
    parent_loops: list[llc.For], array_name: Union[str, int]
) -> list[ArrayRead]:
    result: list[ArrayRead] = []
    for statement in parent_loops[-1].body:
        if isinstance(statement, llc.Phi):
            pass
        elif isinstance(statement, llc.Assign):
            result += [
                ArrayRead(subscript=subscript, parent_loops=parent_loops)
                for subscript in _arrays_read_in_rhs(statement.rhs, array_name)
            ]
        elif isinstance(statement, llc.For):
            result += _arrays_read_in_loop(parent_loops + [statement], array_name)
        else:
            assert_never(statement)
    return result


def _z3_subscript_index_bin_op(
    index: llc.SubscriptIndexBinOp, vars: dict[llc.Var, z3.ArithRef]
) -> z3.ArithRef:
    left = _z3_subscript_index(index.left, vars)
    right = _z3_subscript_index(index.right, vars)
    op = index.operator
    if op is llc.BinOpKind.ADD:
        return left + right
    elif op is llc.BinOpKind.SUB:
        return left - right
    elif op is llc.BinOpKind.MUL:
        return cast(z3.ArithRef, left * right)
    elif op is llc.BinOpKind.DIV:
        return left / right
    else:
        assert op is not llc.BinOpKind.LT
        assert op is not llc.BinOpKind.GT
        assert op is not llc.BinOpKind.LT_E
        assert op is not llc.BinOpKind.GT_E
        assert op is not llc.BinOpKind.EQ
        assert op is not llc.BinOpKind.NOT_EQ
        assert op is not llc.BinOpKind.AND
        assert op is not llc.BinOpKind.OR
        assert op is not llc.BinOpKind.BIT_AND
        assert op is not llc.BinOpKind.BIT_OR
        assert op is not llc.BinOpKind.BIT_XOR
        assert_never(op)


def _z3_subscript_index_unary_op(
    index: llc.SubscriptIndexUnaryOp, vars: dict[llc.Var, z3.ArithRef]
) -> z3.ArithRef:
    op = index.operator
    operand = _z3_subscript_index(index.operand, vars)
    if op is llc.UnaryOpKind.NEGATE:
        return -operand
    else:
        assert op is not llc.UnaryOpKind.NOT
        assert_never(op)


def _z3_subscript_index(
    index: llc.SubscriptIndex, vars: dict[llc.Var, z3.ArithRef]
) -> z3.ArithRef:
    if isinstance(index, llc.Var):
        return vars[index]
    elif isinstance(index, llc.Constant):
        return z3.IntVal(index.value)
    elif isinstance(index, llc.SubscriptIndexBinOp):
        return _z3_subscript_index_bin_op(index, vars)
    elif isinstance(index, llc.SubscriptIndexUnaryOp):
        return _z3_subscript_index_unary_op(index, vars)
    else:
        assert_never(index)


def _check_dep(
    A_def: llc.Update,
    A_use: llc.Subscript,
    i: list[llc.For],
    j: llc.For,
    k: list[llc.For],
) -> bool:
    i_ = [z3.Int(f"i_[{n}]") for n in range(len(i))]
    j_ = z3.Int("j_")
    j__ = z3.Int("j__")
    k_ = [z3.Int(f"k_[{n}]") for n in range(len(k))]
    k__ = [z3.Int(f"k__[{n}]") for n in range(len(k))]
    f = A_def.index
    f_ = A_use.index
    f_ijk = _z3_subscript_index(
        f,
        {ii.counter: ii_ for ii, ii_ in zip(i, i_)}
        | {j.counter: j_}
        | {kk.counter: kk_ for kk, kk_ in zip(k, k_)},
    )
    f__ijk = _z3_subscript_index(
        f_,
        {ii.counter: ii_ for ii, ii_ in zip(i, i_)}
        | {j.counter: j__}
        | {kk.counter: kk_ for kk, kk_ in zip(k, k__)},
    )
    solver = z3.Solver()
    solver.add([0 <= ii for ii in i_])
    solver.add(0 <= j_)
    solver.add(j_ < j__)
    solver.add([0 <= kk for kk in k_])
    solver.add(f_ijk == f__ijk)
    # This check is allowed to have false positives, but not false negatives,
    # so we treat `z3.unknown` the same as `z3.sat`.
    return solver.check() in (z3.sat, z3.unknown)


def _get_k(j: llc.For, A_use: ArrayRead) -> list[llc.For]:
    k = A_use.parent_loops
    assert j == k[0]
    return k[1:]


def _remove_back_edge(A_name: Union[str, int], dep_graph: DepGraph, j: llc.For) -> None:
    """Remove back edge to Phi node in loop j"""
    for A_use in j.body:
        if (
            isinstance(A_use, llc.Phi)
            and isinstance(A_use.lhs, llc.Var)  # needed for mypy
            and A_use.lhs.name == A_name
        ):
            assert dep_graph.enclosing_loops[A_use][-1] == j
            A_defs: list[DepNode] = list(dep_graph.def_use_graph.predecessors(A_use))
            for A_def in A_defs:
                assert isinstance(
                    A_def.lhs, llc.Var
                ), "VectorizedAccesses aren't added until basic vectorization"
                assert A_def.lhs.name == A_name
                if dep_graph.is_back_edge(A_def, A_use):
                    dep_graph.def_use_graph.remove_edge(A_def, A_use)


def _prune_edges_from_loop(i: list[llc.For], j: llc.For, dep_graph: DepGraph) -> None:
    for A_def in _arrays_written_in_loop(j):
        assert isinstance(
            A_def.lhs, llc.Var
        ), "VectorizedAccesses aren't added until basic vectorization"
        A_def_name = A_def.lhs.name
        dep = False
        for A_use in _arrays_read_in_loop([j], A_def_name):
            k = _get_k(j, A_use)
            assert isinstance(A_def.rhs, llc.Update)
            if _check_dep(A_def.rhs, A_use.subscript, i, j, k):
                dep = True
        if not dep:
            _remove_back_edge(A_def_name, dep_graph, j)


def _prune_edges_from_statement(
    enclosing_loops: list[llc.For], statement: llc.Statement, dep_graph: DepGraph
) -> None:
    if isinstance(statement, llc.For):
        loop = statement

        _prune_edges_from_loop(enclosing_loops, loop, dep_graph)

        for statement in loop.body:
            _prune_edges_from_statement(enclosing_loops + [loop], statement, dep_graph)


def remove_infeasible_edges(function: llc.Function, dep_graph: DepGraph) -> None:
    for statement in function.body:
        _prune_edges_from_statement([], statement, dep_graph)


def _find_update(
    A: llc.Var, A_use: llc.Assign, dep_graph: DepGraph
) -> Optional[llc.SubscriptIndex]:
    A_def: DepNode
    A_def = dep_graph.var_to_assignment[A]
    return (
        A_def.rhs.index
        if isinstance(A_def, llc.Assign) and isinstance(A_def.rhs, llc.Update)
        else None
    )


def _refine_array_mux_statement(
    statement: llc.Statement, dep_graph: DepGraph, tmp_var_gen: TempVarGenerator
) -> list[llc.Statement]:
    if isinstance(statement, llc.Assign) and isinstance(statement.rhs, llc.Mux):
        Aj = statement.lhs
        mux = statement.rhs
        c = mux.condition
        Ak = mux.false_value
        Al = mux.true_value
        if (
            isinstance(Aj, llc.Var)
            and isinstance(Ak, llc.Var)
            and isinstance(Al, llc.Var)
        ):
            i1 = _find_update(Ak, statement, dep_graph)
            i2 = _find_update(Al, statement, dep_graph)
            if i1 == i2 and i1 is not None and i2 is not None:
                name = Aj.name
                assert Aj.name == Ak.name == Al.name
                k = Ak.rename_subscript
                l = Al.rename_subscript
                assert k is not None
                assert l is not None
                Ak_i1 = llc.Subscript(Ak, i1)
                Al_i1 = llc.Subscript(Al, i1)
                temp = tmp_var_gen.get()
                return [
                    llc.Assign(
                        lhs=temp,
                        rhs=llc.Mux(c, Ak_i1, Al_i1),
                    ),
                    llc.Assign(
                        lhs=Aj, rhs=llc.Update(llc.Var(f"{name}!{max(k,l)}"), i1, temp)
                    ),
                ]
            else:
                return [statement]
        else:
            return [statement]
    elif isinstance(statement, llc.For):
        return [
            llc.For(
                counter=statement.counter,
                bound_low=statement.bound_low,
                bound_high=statement.bound_high,
                body=_refine_array_mux_statements(
                    statement.body, dep_graph, tmp_var_gen
                ),
            )
        ]
    else:
        return [statement]


def _refine_array_mux_statements(
    stmts: list[llc.Statement], dep_graph: DepGraph, tmp_var_gen: TempVarGenerator
) -> list[llc.Statement]:
    return [
        rstmt
        for stmt in stmts
        for rstmt in _refine_array_mux_statement(stmt, dep_graph, tmp_var_gen)
    ]


def refine_array_mux(
    function: llc.Function, dep_graph: DepGraph
) -> tuple[llc.Function, DepGraph]:
    tmp_var_gen = TempVarGenerator(dep_graph)
    function = llc.Function(
        name=function.name,
        parameters=function.parameters,
        body=_refine_array_mux_statements(function.body, dep_graph, tmp_var_gen),
        return_value=function.return_value,
        return_type=function.return_type,
    )
    dep_graph = DepGraph(function)
    return (function, dep_graph)


def _basic_vectorization_phase_1(
    stmts: list[llc.Statement],
    dep_graph: DepGraph,
    tmp_var_gen: TempVarGenerator,
) -> tuple[list[llc.Statement], list[llc.Statement]]:
    above_loop_result: list[llc.Statement] = []
    inside_loop_result: list[llc.Statement] = []

    for stmt in stmts:
        if isinstance(stmt, (llc.Phi, llc.Assign)):

            def replace_var(
                var: llc.Var,
                stmt: DepNode,
                access_pattern: Optional[llc.SubscriptIndex] = None,
            ) -> llc.Var:
                def_var = dep_graph.var_to_assignment[var]
                edge_kind = dep_graph.edge_kind(def_var, stmt)
                if edge_kind is EdgeKind.SAME_LEVEL:
                    return var
                elif edge_kind is EdgeKind.OUTER_TO_INNER:
                    var_prime = tmp_var_gen.get()
                    above_loop_result.append(
                        llc.Assign(
                            lhs=var_prime,
                            rhs=LiftExpr(
                                Subscript(var, access_pattern)
                                if access_pattern
                                else var,
                                tuple(
                                    (loop.counter, loop.bound_high)
                                    for loop in dep_graph.enclosing_loops[stmt]
                                ),
                            ),
                        )
                    )
                    return var_prime
                elif edge_kind is EdgeKind.INNER_TO_OUTER:
                    var_prime = tmp_var_gen.get()
                    inside_loop_result.append(
                        llc.Assign(
                            lhs=var_prime,
                            rhs=DropDim(
                                var,
                                tuple(
                                    loop.bound_high
                                    for loop in dep_graph.enclosing_loops[def_var]
                                ),
                            ),
                        )
                    )
                    return var_prime
                else:
                    assert_never(edge_kind)

            def replace_atom(atom: llc.Atom, stmt: DepNode) -> llc.Atom:
                if isinstance(atom, llc.Var):
                    return replace_var(atom, stmt)
                elif isinstance(atom, llc.Constant):
                    return atom
                else:
                    assert_never(atom)

            def replace_subscript(
                sub: llc.Subscript, stmt: DepNode
            ) -> Union[llc.Subscript, Var]:
                replaced_arr = replace_var(sub.array, stmt, sub.index)
                if replaced_arr != sub:
                    return replaced_arr
                else:
                    return sub

            def replace_operand(o: llc.Operand, stmt: DepNode) -> llc.Operand:
                if isinstance(o, (llc.Var, llc.Constant)):
                    return replace_atom(o, stmt)
                elif isinstance(o, llc.Subscript):
                    return replace_subscript(o, stmt)
                elif isinstance(o, llc.BinOp):
                    return llc.BinOp(
                        operator=o.operator,
                        left=replace_operand(o.left, stmt),
                        right=replace_operand(o.right, stmt),
                    )
                elif isinstance(o, llc.UnaryOp):
                    return llc.UnaryOp(
                        operator=o.operator, operand=replace_operand(o.operand, stmt)
                    )
                else:
                    assert not isinstance(
                        o, VectorizedAccess
                    ), "there shouldn't be any vectorized arrays before basic vectorization"
                    assert_never(o)

            if isinstance(stmt, llc.Phi):
                assert isinstance(
                    stmt.rhs_false, llc.Var
                ), "VectorizedAccesses are not added until after this phase"
                stmt.rhs_false = replace_var(stmt.rhs_false, stmt)
                assert isinstance(
                    stmt.rhs_true, llc.Var
                ), "VectorizedAccesses are not added until after this phase"
                stmt.rhs_true = replace_var(stmt.rhs_true, stmt)
            elif isinstance(stmt, llc.Assign):
                if isinstance(stmt.rhs, llc.Var):
                    stmt.rhs = replace_var(stmt.rhs, stmt)
                elif isinstance(stmt.rhs, llc.Constant):
                    pass
                elif isinstance(stmt.rhs, llc.Subscript):
                    stmt.rhs = replace_subscript(stmt.rhs, stmt)
                elif isinstance(stmt.rhs, llc.BinOp):
                    stmt.rhs.left = replace_operand(stmt.rhs.left, stmt)
                    stmt.rhs.right = replace_operand(stmt.rhs.right, stmt)
                elif isinstance(stmt.rhs, llc.UnaryOp):
                    stmt.rhs.operand = replace_operand(stmt.rhs.operand, stmt)
                elif isinstance(stmt.rhs, llc.List):
                    replaced = [replace_atom(atom, stmt) for atom in stmt.rhs.items]
                    stmt.rhs = llc.List(
                        [
                            v.array if isinstance(v, VectorizedAccess) else v
                            for v in replaced
                        ]
                    )
                elif isinstance(stmt.rhs, llc.Tuple):
                    replaced = [replace_atom(atom, stmt) for atom in stmt.rhs.items]
                    stmt.rhs = llc.Tuple(
                        [
                            v.array if isinstance(v, VectorizedAccess) else v
                            for v in replaced
                        ]
                    )
                elif isinstance(stmt.rhs, llc.Mux):
                    stmt.rhs.false_value = replace_operand(stmt.rhs.false_value, stmt)
                    stmt.rhs.true_value = replace_operand(stmt.rhs.true_value, stmt)
                else:
                    assert not isinstance(
                        stmt.rhs, llc.Update
                    ), "Basic Vectorization does not support array writes for now"
                    assert not isinstance(
                        stmt.rhs, (LiftExpr, DropDim, VectorizedAccess)
                    ), "These types are introduced in basic vectorization so they shouldn't exist here"
                    assert_never(stmt.rhs)
            else:
                assert_never(stmt)

            inside_loop_result.append(stmt)

        elif isinstance(stmt, llc.For):
            for_outside_stmts, for_inside_stmts = _basic_vectorization_phase_1(
                stmt.body, dep_graph, tmp_var_gen
            )
            inside_loop_result += for_outside_stmts
            new_loop = llc.For(
                counter=stmt.counter,
                bound_low=stmt.bound_low,
                bound_high=stmt.bound_high,
                body=for_inside_stmts,
            )
            dep_graph.enclosing_loops[new_loop] = dep_graph.enclosing_loops[stmt]

            inside_loop_result.append(new_loop)
        else:
            assert_never(stmt)

    return above_loop_result, inside_loop_result


def _find_loop_depth(stmts: list[llc.Statement]) -> int:
    return max(
        1 + _find_loop_depth(stmt.body) if isinstance(stmt, llc.For) else 0
        for stmt in stmts
    )


def _basic_vectorization_phase_2(
    stmts: list[llc.Statement],
    type_env: TypeEnv,
    dep_graph: DepGraph,
    tmp_var_gen: TempVarGenerator,
    tgt_depth: int,
    loop_stack: list[llc.For] = [],
) -> list[llc.Statement]:
    # If we're lower than the target depth, just recursively call this function
    if len(loop_stack) < tgt_depth:
        ret: list[llc.Statement] = []
        for stmt in stmts:
            if isinstance(stmt, llc.For):
                # If we're updating the next level, it will handle recreating loops
                if len(loop_stack) == tgt_depth - 1:
                    ret.extend(
                        _basic_vectorization_phase_2(
                            stmt.body,
                            type_env,
                            dep_graph,
                            tmp_var_gen,
                            tgt_depth,
                            loop_stack + [stmt],
                        ),
                    )
                else:
                    ret.append(
                        dc.replace(
                            stmt,
                            body=_basic_vectorization_phase_2(
                                stmt.body,
                                type_env,
                                dep_graph,
                                tmp_var_gen,
                                tgt_depth,
                                loop_stack + [stmt],
                            ),
                        )
                    )
            else:
                ret.append(stmt)
        return ret

    # Otherwise, we're modifying this layer of the loop nest
    # We assume that all deeper loops have been handled already.

    # We now can determine which statements must be in the reconstructed monolithic
    # for loop.  A statement is in the reconstructed loop if it is part of a closure with
    # one of the surrounding loop's phi nodes or if it uses the loop counter.
    phis = set(phi for phi in stmts if isinstance(phi, llc.Phi))
    raw_closures = defaultdict(list)
    vectorizeable = []
    for idx, stmt in enumerate(stmts):
        added_to_closure = False
        for phi in phis:
            if dep_graph.has_same_level_path(
                phi, stmt
            ) and dep_graph.has_same_level_path(stmt, phi):
                added_to_closure = True
                raw_closures[phi].append((idx, stmt))

        if not added_to_closure:
            vectorizeable.append(stmt)

    # Merge closures
    closures = []
    used_phis = set()
    for phi, closure_stmts in raw_closures.items():
        if phi in used_phis:
            continue

        used_phis.add(phi)

        # Check over every unmerged closure to see if it can be
        # merged with this one
        for other_phi, other_closure_stmts in raw_closures.items():
            if other_phi in used_phis:
                continue

            if any(
                stmt[0] == other_stmt[0]
                for stmt, other_stmt in zip(closure_stmts, other_closure_stmts)
            ):
                used_phis.add(other_phi)
                raw_closures[phi].extend(other_closure_stmts)

        # Sort the statements in the closure by their index to retain def-use order
        raw_closures[phi].sort(key=lambda x: x[0])

        # Drop any duplicate statements
        closure = []
        used_indices = set()
        for idx, stmt in raw_closures[phi]:
            if idx not in used_indices:
                closure.append(stmt)
                used_indices.add(idx)

        closures.append((phi, closure))

    # Helper function to generate a monolithic for loop from a closure
    def generate_monolithic_for(
        closure: list[llc.Statement], lifted_vars: dict[llc.Var, VectorizedAccess]
    ) -> llc.For:
        # Create new loop
        new_counter = tmp_var_gen.get()
        type_env[new_counter] = type_env[loop_stack[-1].counter]
        monolithic_for = dc.replace(
            loop_stack[-1],
            counter=new_counter,
            body=closure,
            is_monolithic=True,
        )

        def unvectorize_loop_dim(stmt):
            if isinstance(stmt, (list, tuple)):
                for sub_stmt in stmt:
                    unvectorize_loop_dim(sub_stmt)
            elif dc.is_dataclass(stmt):
                for field in dc.fields(stmt):
                    val = getattr(stmt, field.name)
                    if isinstance(val, VectorizedAccess):
                        new_vectorization = tuple(
                            vectorization if dim != monolithic_for.counter else False
                            for dim, vectorization in zip(
                                val.idx_vars, val.vectorized_dims
                            )
                        )
                        setattr(
                            stmt,
                            field.name,
                            dc.replace(val, vectorized_dims=new_vectorization),
                        )
                    else:
                        unvectorize_loop_dim(val)

        monolithic_for = util.replace_pattern(
            monolithic_for, loop_stack[-1].counter, monolithic_for.counter
        )
        for orig_var, lifted in lifted_vars.items():
            monolithic_for = util.replace_pattern(monolithic_for, orig_var, lifted)
        unvectorize_loop_dim(monolithic_for)
        return monolithic_for

    def uses_loop_counter(stmt) -> bool:
        if not loop_stack:
            return False

        if stmt == loop_stack[-1].counter:
            return True
        elif isinstance(stmt, (list, tuple)):
            return any(uses_loop_counter(item) for item in stmt)
        elif isinstance(stmt, VectorizedAccess):
            return any(
                uses_loop_counter(item)
                for item, vectorized in zip(stmt.idx_vars, stmt.vectorized_dims)
                if not vectorized
            )
        elif isinstance(stmt, llc.LiftExpr):
            # If the loop counter is bound in the lifted expression,
            # we can ignore it
            if any(idx == loop_stack[-1].counter for idx, _ in stmt.dims):
                return False
            # Otherwise, it's a free variable in the loop counter so
            # we need to lift it
            else:
                return uses_loop_counter(stmt.expr)
        elif dc.is_dataclass(stmt):
            return any(
                uses_loop_counter(getattr(stmt, field.name))
                for field in dc.fields(stmt)
            )
        else:
            return False

    def lift_vars(
        stmt: llc.Statement,
    ) -> dict[llc.Var, tuple[llc.Assign, VectorizedAccess]]:
        if isinstance(stmt, llc.Assign):
            if uses_loop_counter(stmt):
                new_rhs = LiftExpr(
                    stmt.rhs,
                    ((loop_stack[-1].counter, loop_stack[-1].bound_high),),
                )
                new_var = tmp_var_gen.get()
                if isinstance(stmt.lhs, Var):
                    orig_var = stmt.lhs
                else:
                    orig_var = stmt.lhs.array
                new_var_type = type_env[orig_var].add_dim()
                if new_var_type.dim_sizes is not None:
                    new_var_type.dim_sizes.append(
                        (
                            loop_stack[-1].counter,
                            loop_stack[-1].bound_high,
                        )
                    )
                else:
                    new_var_type.dim_sizes = [
                        (loop_stack[-1].counter, loop_stack[-1].bound_high)
                    ]
                assert new_var_type.dim_sizes is not None
                assert new_var_type.dims is not None

                lifted_access = VectorizedAccess(
                    new_var,
                    tuple(bound for _, bound in new_var_type.dim_sizes),
                    tuple([True] * (new_var_type.dims - 1) + [False]),
                    tuple(var for var, _ in new_var_type.dim_sizes),
                )

                type_env[new_var] = new_var_type
                return {orig_var: (llc.Assign(new_var, new_rhs), lifted_access)}
            else:
                return {}
        elif isinstance(stmt, llc.For):
            return {
                var: assign
                for substmt in stmt.body
                for var, assign in lift_vars(substmt).items()
            }
        elif isinstance(stmt, llc.Phi):
            return {}
        else:
            assert_never(stmt)

    # Generate output
    output: list[llc.Statement] = []
    used_closures = set()
    lifted_arrs: dict[llc.Var, VectorizedAccess] = {}
    for stmt in vectorizeable:
        for phi, closure in closures:
            if phi in used_closures:
                continue

            # of creating a new for loop to hold the closure's contents, unvectorizing the loop's
            # dimension, and updating the dependency graph.
            if any(
                dep_graph.has_same_level_path(closure_stmt, stmt)
                for closure_stmt in closure
            ):
                used_closures.add(phi)
                output.append(generate_monolithic_for(closure, lifted_arrs))

        # Now that all needed closures have been added, add this statement.  If it needs to be lifted,
        # then lift all substatements.
        if uses_loop_counter(stmt):
            lifted = lift_vars(stmt)
            for orig_var, val in lifted.items():
                assignment, lifted_access = val
                lifted_arrs[orig_var] = lifted_access
                output.append(assignment)
        else:
            output.append(stmt)

    # Add any remaining closures
    for phi, closure in closures:
        if phi not in used_closures:
            output.append(generate_monolithic_for(closure, lifted_arrs))

    return output


def basic_vectorization_phase_1(
    function: llc.Function, dep_graph: DepGraph
) -> tuple[llc.Function, DepGraph]:
    tmp_var_gen = TempVarGenerator(dep_graph)

    before_func, body = _basic_vectorization_phase_1(
        function.body, dep_graph, tmp_var_gen
    )
    assert not before_func

    function = llc.Function(
        name=function.name,
        parameters=function.parameters,
        body=body,
        return_value=function.return_value,
        return_type=function.return_type,
    )
    return function, DepGraph(function)


def basic_vectorization_phase_2(
    function: llc.Function, type_env: TypeEnv, dep_graph: DepGraph
) -> tuple[llc.Function, TypeEnv, DepGraph]:
    tmp_var_gen = TempVarGenerator(dep_graph)

    loop_depth = _find_loop_depth(function.body) + 1
    for d in reversed(range(loop_depth)):
        dep_graph = DepGraph(function)
        body = _basic_vectorization_phase_2(
            function.body, type_env, dep_graph, tmp_var_gen, d
        )

        function = llc.Function(
            name=function.name,
            parameters=function.parameters,
            body=body,
            return_value=function.return_value,
            return_type=function.return_type,
        )

    return (function, type_env, DepGraph(function))
