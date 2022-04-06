from collections import defaultdict
import functools

from .ast_shared import TypeEnv, Var, VectorizedAccess, Subscript, DataType
from .tac_cfg import DropDim, LiftExpr, Assign, BinOp, BinOpKind
from . import loop_linear_code as llc
from .dep_graph import DepGraph, DepNode, EdgeKind, DepParameter
from . import util
from .util import assert_never
from .type_analysis import collect_idx_vars

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
        var_names = [
            stmt.lhs.name if isinstance(stmt.lhs, llc.Var) else stmt.lhs.array.name
            for stmt in nodes
            # Return statements assign no variable
            if not isinstance(stmt, llc.Return)
        ]
        self._max_temp_var_num = max(
            [0 if isinstance(name, str) else name for name in var_names]
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
        if isinstance(statement, (llc.Phi, llc.Return)):
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
    # TODO: is it correct to ignore LiftExpr, DropDim, VectorizedArr, and VectorizedAccess?
    if isinstance(
        rhs,
        (
            llc.Var,
            llc.Constant,
            LiftExpr,
            DropDim,
            VectorizedAccess,
            llc.VectorizedUpdate,
        ),
    ):
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
        if isinstance(statement, (llc.Phi, llc.Return)):
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
            A_use.targetless = True
            """
            NOTE: because we want to keep the back edges for basic vectorization, the below
            code to remove all back edges is commented out.

            assert dep_graph.enclosing_loops[A_use][-1] == j
            A_defs: list[DepNode] = list(dep_graph.def_use_graph.predecessors(A_use))
            for A_def in A_defs:
                assert not isinstance(
                    A_def, llc.Return
                ), "Return statements have no successors in the dependency graph"
                assert isinstance(
                    A_def.lhs, llc.Var
                ), "VectorizedAccesses aren't added until basic vectorization"
                assert A_def.lhs.name == A_name
                if dep_graph.is_back_edge(A_def, A_use):
                    dep_graph.def_use_graph.remove_edge(A_def, A_use)
            """


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
        return_type=function.return_type,
    )
    dep_graph = DepGraph(function)
    return (function, dep_graph)


def _basic_vectorization_phase_1(
    stmts: list[llc.Statement],
    dep_graph: DepGraph,
    type_env: TypeEnv,
    tmp_var_gen: TempVarGenerator,
) -> tuple[list[llc.Statement], list[llc.Statement], list[llc.Statement]]:
    above_loop_result: list[llc.Statement] = []
    inside_loop_result: list[llc.Statement] = []
    after_loop_result: list[llc.Statement] = []

    for stmt in stmts:

        def replace_var(
            var: llc.Var,
            stmt: DepNode,
            access_pattern: Optional[llc.SubscriptIndex] = None,
            lhs_dims: Optional[list[llc.LoopBound]] = None
        ) -> llc.Var:
            def_var = dep_graph.var_to_assignment[var]
            edge_kind = dep_graph.edge_kind(def_var, stmt)

            # def_var -> stmt

            if edge_kind is EdgeKind.SAME_LEVEL:
                return var
            elif edge_kind is EdgeKind.OUTER_TO_INNER:
                var_prime = tmp_var_gen.get()
                var_dims = type_env[var].dim_sizes
                if var_dims is None:
                    if lhs_dims is not None:
                        dims = tuple((Var("_"), dim_size) for dim_size in lhs_dims)
                    else:
                        dims = tuple(
                            (loop.counter, loop.bound_high)
                            for loop in dep_graph.enclosing_loops[stmt]
                        )
                else:
                    dims = tuple((Var("_"), dim_size) for dim_size in var_dims)

                above_loop_result.append(
                    llc.Assign(
                        lhs=var_prime,
                        rhs=LiftExpr(
                            Subscript(var, access_pattern) if access_pattern else var,
                            dims,
                        ),
                    )
                )
                return var_prime
            elif edge_kind is EdgeKind.INNER_TO_OUTER:
                canonical_dimensionality = type_env[var].unvectorized_dims
                assert canonical_dimensionality is not None
                enclosure_dimensionality = len(dep_graph.enclosing_loops[def_var])
                if enclosure_dimensionality <= canonical_dimensionality:
                    return var

                var_prime = tmp_var_gen.get()
                drop_dim = llc.Assign(
                    lhs=var_prime,
                    rhs=DropDim(
                        var,
                        tuple(
                            loop.bound_high
                            for loop in dep_graph.enclosing_loops[def_var]
                        ),
                    ),
                )
                # If this is being used by a phi node, then the definition occurs after the
                # phi node, so we should insert the drop dim at the end of the current loop
                if isinstance(stmt, llc.Phi):
                    after_loop_result.append(drop_dim)
                # If this isn't a phi node, then the definition occurs before the use statement
                # so we should insert the drop dim right before the use statement
                else:
                    inside_loop_result.append(drop_dim)
                return var_prime
            else:
                assert_never(edge_kind)

        def replace_atom(atom: llc.Atom, stmt: DepNode) -> llc.Atom:
            if isinstance(atom, llc.Var):
                return replace_var(atom, stmt)
            elif isinstance(atom, llc.Constant):
                return atom
            else:
                assert not isinstance(atom, llc.VectorizedAccess)
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

        if isinstance(stmt, (llc.Phi, llc.Assign)):

            if isinstance(stmt, llc.Phi):
                assert isinstance(stmt.lhs, llc.Var), "VectorizedAccesses are not added until after this phase"
                lhs_dims = type_env[stmt.lhs].dim_sizes
                assert isinstance(
                    stmt.rhs_false, llc.Var
                ), "VectorizedAccesses are not added until after this phase"
                stmt.rhs_false = replace_var(stmt.rhs_false, stmt, lhs_dims=lhs_dims)
                assert isinstance(
                    stmt.rhs_true, llc.Var
                ), "VectorizedAccesses are not added until after this phase"
                stmt.rhs_true = replace_var(stmt.rhs_true, stmt, lhs_dims=lhs_dims)
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
                    stmt.rhs.condition = replace_var(stmt.rhs.condition, stmt)
                    stmt.rhs.false_value = replace_operand(stmt.rhs.false_value, stmt)
                    stmt.rhs.true_value = replace_operand(stmt.rhs.true_value, stmt)
                elif isinstance(stmt.rhs, llc.Update):
                    new_val = replace_atom(stmt.rhs.value, stmt)
                    dim_sizes = tuple(
                        loop.bound_high for loop in dep_graph.enclosing_loops[stmt]
                    )
                    vectorized_dims = tuple(
                        True for _ in dep_graph.enclosing_loops[stmt]
                    )
                    idx_vars = tuple(
                        loop.counter for loop in dep_graph.enclosing_loops[stmt]
                    )
                    stmt.rhs = llc.VectorizedUpdate(
                        array=stmt.rhs.array,
                        dim_sizes=dim_sizes,
                        vectorized_dims=vectorized_dims,
                        idx_vars=idx_vars,
                        value=new_val,
                    )
                else:
                    assert not isinstance(
                        stmt.rhs,
                        (LiftExpr, DropDim, VectorizedAccess, llc.VectorizedUpdate),
                    ), "These types are introduced in basic vectorization so they shouldn't exist here"
                    assert_never(stmt.rhs)
            else:
                assert_never(stmt)

            inside_loop_result.append(stmt)

        elif isinstance(stmt, llc.For):
            (
                for_outside_stmts,
                for_inside_stmts,
                for_after_stmts,
            ) = _basic_vectorization_phase_1(
                stmt.body, dep_graph, type_env, tmp_var_gen
            )
            inside_loop_result += for_outside_stmts
            for_inside_stmts += for_after_stmts
            new_loop = llc.For(
                counter=stmt.counter,
                bound_low=stmt.bound_low,
                bound_high=stmt.bound_high,
                body=for_inside_stmts,
            )
            dep_graph.enclosing_loops[new_loop] = dep_graph.enclosing_loops[stmt]

            inside_loop_result.append(new_loop)

        elif isinstance(stmt, llc.Return):
            new_var = replace_var(stmt.value, stmt)
            inside_loop_result.append(llc.Return(new_var))

        else:
            assert_never(stmt)

    return above_loop_result, inside_loop_result, after_loop_result

def _finalize_drop_dims(stmts: list[llc.Statement], dep_graph: DepGraph):
    """
    Replace all drop_dim() expressions targetting a variable assigned by a phi node
    with the rhs_true value of the phi node.  This cannot be done during the initial
    pass of vectorization phase 1 as the rhs_true value may be replaced.
    """
    for stmt in stmts:
        if isinstance(stmt, llc.Assign) and isinstance(stmt.rhs, DropDim):
            drop_expr = stmt.rhs.array
            if isinstance(drop_expr, VectorizedAccess):
                drop_expr = drop_expr.array

            drop_expr_assignment = dep_graph.var_to_assignment[drop_expr]

            if isinstance(drop_expr_assignment, llc.Phi):
                corrected_drop_expr = drop_expr_assignment.rhs_true
                if isinstance(corrected_drop_expr, VectorizedAccess):
                    corrected_drop_expr = corrected_drop_expr.array
                stmt.rhs = dc.replace(stmt.rhs, array=corrected_drop_expr)
        elif isinstance(stmt, llc.For):
            _finalize_drop_dims(stmt.body, dep_graph)


def _merge_vectorized_accesses(
    vectorized_accesses: list[Optional[VectorizedAccess]],
    enclosing_loops: list[llc.For],
    take_longest_access=False,
) -> Optional[VectorizedAccess]:
    if all(access is None for access in vectorized_accesses):
        return None

    all_dim_sizes = set(access.dim_sizes for access in vectorized_accesses if access)
    all_vectorized_dims = set(
        access.vectorized_dims
        for access in vectorized_accesses
        if access and not all(access.vectorized_dims)
    )
    all_idx_vars = set(
        access.idx_vars
        for access in vectorized_accesses
        if access
        # Ignore accesses which are BinOps (these come from phi nodes with backedges)
        and not any(isinstance(var, llc.BinOp) for var in access.idx_vars)
    )

    if len(all_dim_sizes) != 1:
        if take_longest_access:
            all_dim_sizes = set([max(all_dim_sizes, key=len)])
        else:
            raise TypeError(
                f"Expected all dim sizes to be the same but got {all_dim_sizes}"
            )

    # If all of the provided vectorized_dims are True, then we can synthesize this here
    # We need to have separate handling for this case because lift expressions are added
    if len(all_vectorized_dims) == 0:
        num_dims = set(len(dim_sizes) for dim_sizes in all_dim_sizes)
        assert len(num_dims) == 1
        all_vectorized_dims = set(((True,) * num_dims.pop(),))

    if len(all_vectorized_dims) != 1:
        if take_longest_access:
            all_dim_sizes = set([max(all_dim_sizes, key=len)])
        else:
            raise TypeError(
                f"Expected all vectorized dims to be the same but got {all_vectorized_dims}"
            )

    if len(all_idx_vars) != 1:
        if take_longest_access:
            all_idx_vars = set([max(all_idx_vars, key=len)])
        else:
            loop_enclosure_vars = tuple(loop.counter for loop in enclosing_loops)
            assert (
                loop_enclosure_vars in all_idx_vars
            ), f"Expected all idx vars to be the same but got {all_idx_vars}"
            all_idx_vars = set((loop_enclosure_vars,))

    return VectorizedAccess(
        array=None,  # type: ignore
        dim_sizes=all_dim_sizes.pop(),
        vectorized_dims=all_vectorized_dims.pop(),
        idx_vars=all_idx_vars.pop(),
    )


def _collect_vectorized_access(
    expr: llc.AssignRHS,
    vectorized_accesses: dict[llc.Var, VectorizedAccess],
    enclosing_loops: list[llc.For],
) -> Optional[VectorizedAccess]:
    if isinstance(expr, llc.Var):
        return vectorized_accesses.get(expr)

    elif isinstance(expr, llc.LiftExpr):
        return VectorizedAccess(
            array=None,  # type: ignore
            dim_sizes=tuple(dim_size for _idx_var, dim_size in expr.dims),
            vectorized_dims=tuple(True for _ in expr.dims),
            idx_vars=tuple(idx_var for idx_var, _dim_size in expr.dims),
        )

    elif isinstance(expr, (llc.DropDim, llc.Subscript)):
        var = expr.array
        if isinstance(var, VectorizedAccess):
            var = var.array

        if var not in vectorized_accesses:
            return None
        var_vectorized = vectorized_accesses[var]
        return VectorizedAccess(
            array=None,  # type: ignore
            dim_sizes=var_vectorized.dim_sizes[:-1],
            vectorized_dims=var_vectorized.vectorized_dims[:-1],
            idx_vars=var_vectorized.idx_vars[:-1],
        )

    elif isinstance(expr, llc.BinOp):
        return _merge_vectorized_accesses(
            [
                _collect_vectorized_access(
                    expr.left, vectorized_accesses, enclosing_loops
                ),
                _collect_vectorized_access(
                    expr.right, vectorized_accesses, enclosing_loops
                ),
            ],
            enclosing_loops,
        )

    elif isinstance(expr, llc.UnaryOp):
        return _collect_vectorized_access(
            expr.operand, vectorized_accesses, enclosing_loops
        )

    elif isinstance(expr, llc.Mux):
        return _merge_vectorized_accesses(
            [
                _collect_vectorized_access(
                    expr.false_value, vectorized_accesses, enclosing_loops
                ),
                _collect_vectorized_access(
                    expr.true_value, vectorized_accesses, enclosing_loops
                ),
            ],
            enclosing_loops,
        )

    elif isinstance(expr, llc.VectorizedAccess):
        # After phase 2 we might need to update vectorized accesses, so we should
        # only return a vectorized access if its definition has been visited before
        # (i.e. we've confirmed its correct dimensionality)
        if expr.array in vectorized_accesses:
            return expr
        return None

    elif isinstance(expr, (llc.Update, llc.VectorizedUpdate)):
        return _collect_vectorized_access(
            expr.array, vectorized_accesses, enclosing_loops
        )

    elif isinstance(expr, (llc.Constant, llc.List, llc.Tuple)):
        return None

    else:
        assert_never(expr)


def _update_vectorized_accesses(
    expr: llc.AssignRHS, vectorized_accesses: dict[llc.Var, VectorizedAccess]
) -> llc.AssignRHS:
    if isinstance(expr, llc.Var):
        if expr in vectorized_accesses:
            return vectorized_accesses[expr]
        else:
            return expr
    elif isinstance(expr, VectorizedAccess):
        # In the case where a lift expression was lifted out of a loop in phase 2 of vectorization,
        # we need to update the vectorized accesses to reflect the new array.
        if expr.array not in vectorized_accesses:
            return expr

        new_arr = vectorized_accesses[expr.array]
        # Only earlier dimensions can be added, so we're free to prepend the new dims
        new_vectorized_dims = [True] * (
            len(new_arr.vectorized_dims) - len(expr.vectorized_dims)
        ) + list(expr.vectorized_dims)
        new_idx_vars = list(new_arr.idx_vars)[: -len(expr.vectorized_dims)] + list(
            expr.idx_vars
        )
        return dc.replace(
            new_arr,
            vectorized_dims=tuple(new_vectorized_dims),
            idx_vars=tuple(new_idx_vars),
        )
    elif isinstance(expr, llc.Subscript):
        if expr.array in vectorized_accesses:
            vectorized_access = vectorized_accesses[expr.array]
            # TODO: handle more complex indexing than just a single variable
            new_vectorized_dims = tuple(
                vectorized
                if not (
                    isinstance(expr.index, llc.Var) and idx_var.name == expr.index.name
                )
                else False
                for vectorized, idx_var in zip(
                    vectorized_access.vectorized_dims, vectorized_access.idx_vars
                )
            )

            new_idx_vars = tuple(
                idx_var
                if not (
                    isinstance(expr.index, llc.Var) and idx_var.name == expr.index.name
                )
                else expr.index
                for idx_var in vectorized_access.idx_vars
            )

            return dc.replace(
                vectorized_access,
                vectorized_dims=new_vectorized_dims,
                idx_vars=new_idx_vars,
            )
        else:
            return expr
    elif dc.is_dataclass(expr):
        return dc.replace(
            expr,
            **{
                field.name: _update_vectorized_accesses(
                    getattr(expr, field.name), vectorized_accesses
                )
                for field in dc.fields(expr)
            },
        )
    else:
        return expr


def _assign_vectorized_accesses(func: llc.Function, dep_graph: DepGraph):
    worklist = list(dep_graph.def_use_graph.nodes)
    vectorized_accesses: dict[llc.Var, VectorizedAccess] = {}

    while worklist:
        stmt = worklist.pop()

        if isinstance(stmt, (DepParameter, llc.For, llc.Return)):
            continue

        elif isinstance(stmt, llc.Phi):
            rhs_true = _update_vectorized_accesses(stmt.rhs_true, vectorized_accesses)
            assert isinstance(rhs_true, (llc.Var, VectorizedAccess))
            stmt.rhs_true = rhs_true

            rhs_false = _update_vectorized_accesses(stmt.rhs_false, vectorized_accesses)
            assert isinstance(rhs_false, (llc.Var, VectorizedAccess))
            stmt.rhs_false = rhs_false

            rhs_access = _merge_vectorized_accesses(
                [
                    _collect_vectorized_access(
                        stmt.rhs_false,
                        vectorized_accesses,
                        dep_graph.enclosing_loops[stmt],
                    ),
                    _collect_vectorized_access(
                        stmt.rhs_true,
                        vectorized_accesses,
                        dep_graph.enclosing_loops[stmt],
                    ),
                ],
                dep_graph.enclosing_loops[stmt],
                take_longest_access=True,
            )
        elif isinstance(stmt, llc.Assign):
            stmt.rhs = _update_vectorized_accesses(stmt.rhs, vectorized_accesses)
            rhs_access = _collect_vectorized_access(
                stmt.rhs, vectorized_accesses, dep_graph.enclosing_loops[stmt]
            )
        else:
            assert_never(stmt)

        if (
            rhs_access is None
            or len(rhs_access.dim_sizes) == 0
            or isinstance(stmt.lhs, llc.VectorizedAccess)
        ):
            continue

        lhs_access = dc.replace(rhs_access, array=stmt.lhs)
        vectorized_accesses[stmt.lhs] = lhs_access
        stmt.lhs = lhs_access

        worklist.extend([edge[1] for edge in dep_graph.def_use_graph.edges(stmt)])


def _find_loop_depth(stmts: list[llc.Statement]) -> int:
    return max(
        1 + _find_loop_depth(stmt.body) if isinstance(stmt, llc.For) else 0
        for stmt in stmts
    )


def _replace_in_rhs(
    stmt: llc.Statement, pattern: llc.AssignRHS, replacement: llc.AssignRHS
) -> llc.Statement:
    if isinstance(stmt, llc.Assign):
        new_rhs = util.replace_pattern(stmt.rhs, pattern, replacement)
        return dc.replace(stmt, rhs=new_rhs)
    elif isinstance(stmt, llc.Phi):
        rhs_vars = util.replace_pattern(stmt.rhs_vars, pattern, replacement)
        return dc.replace(stmt, rhs_vars=rhs_vars)
    elif isinstance(stmt, llc.For):
        new_body = [
            _replace_in_rhs(substmt, pattern, replacement) for substmt in stmt.body
        ]
        return dc.replace(stmt, body=new_body)
    elif isinstance(stmt, llc.Return):
        new_return = dc.replace(stmt)
        return util.replace_pattern(
            new_return, pattern, replacement, include_return=True
        )
    else:
        assert_never(stmt)


def _basic_vectorization_phase_2(
    stmts: list[llc.Statement],
    dep_graph: DepGraph,
    tmp_var_gen: TempVarGenerator,
    tgt_depth: int,
    loop_stack: list[llc.For] = [],
) -> tuple[list[llc.Statement], dict[llc.Var, llc.Var]]:
    # If we're lower than the target depth, just recursively call this function
    if len(loop_stack) < tgt_depth:
        ret: list[llc.Statement] = []
        phi_renames = {}
        for stmt in stmts:
            if isinstance(stmt, llc.For):
                # If we're updating the next level, it will handle recreating loops
                if len(loop_stack) == tgt_depth - 1:
                    new_loop, local_phi_renames = _basic_vectorization_phase_2(
                        stmt.body,
                        dep_graph,
                        tmp_var_gen,
                        tgt_depth,
                        loop_stack + [stmt],
                    )
                    ret.extend(new_loop)
                    phi_renames.update(local_phi_renames)
                else:
                    loop_body, local_phi_renames = _basic_vectorization_phase_2(
                        stmt.body,
                        dep_graph,
                        tmp_var_gen,
                        tgt_depth,
                        loop_stack + [stmt],
                    )
                    ret.append(dc.replace(stmt, body=loop_body))
                    phi_renames.update(local_phi_renames)
            else:
                ret.append(stmt)
        return ret, phi_renames

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

    def collect_updated_array_names(stmts: list[llc.Statement]) -> list[str]:
        updated_arr_names = []
        for stmt in stmts:
            if isinstance(stmt, llc.Assign) and isinstance(
                stmt.rhs, (llc.VectorizedUpdate, llc.Update)
            ):
                arr = stmt.rhs.array
                if isinstance(arr, llc.VectorizedAccess):
                    arr = arr.array
                updated_arr_names.append(str(arr.name))
            elif isinstance(stmt, llc.For):
                updated_arr_names.extend(collect_updated_array_names(stmt.body))
        return updated_arr_names

    def closures_intersect(
        c1: list[tuple[int, llc.Statement]], c2: list[tuple[int, llc.Statement]]
    ) -> bool:
        # Check for shared statements
        c1_stmt_idxs = set(idx for idx, _ in c1)
        c2_stmt_idxs = set(idx for idx, _ in c2)
        if len(c1_stmt_idxs & c2_stmt_idxs) > 0:
            return True

        # Check for shared updated arrays
        c1_updated_arrs = set(collect_updated_array_names([stmt for _, stmt in c1]))
        c2_updated_arrs = set(collect_updated_array_names([stmt for _, stmt in c2]))
        if len(c1_updated_arrs & c2_updated_arrs) > 0:
            return True

        # Check for targetless phi nodes
        c1_phi_arrs = set(
            str(phi.lhs.name)
            if isinstance(phi.lhs, llc.Var)
            else str(phi.lhs.array.name)
            for phi in [stmt for _, stmt in c1 if isinstance(stmt, llc.Phi)]
        )
        c2_phi_arrs = set(
            str(phi.lhs.name)
            if isinstance(phi.lhs, llc.Var)
            else str(phi.lhs.array.name)
            for phi in [stmt for _, stmt in c2 if isinstance(stmt, llc.Phi)]
        )
        if (
            len(c1_updated_arrs & c2_phi_arrs) > 0
            or len(c2_updated_arrs & c1_phi_arrs) > 0
        ):
            return True

        return False

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

            if closures_intersect(closure_stmts, other_closure_stmts):
                used_phis.add(other_phi)
                closure_stmts.extend(other_closure_stmts)

        # Sort the statements in the closure by their index to retain def-use order
        closure_stmts.sort(key=lambda x: x[0])

        # Drop any duplicate statements
        closure = []
        used_indices = set()
        for idx, stmt in closure_stmts:
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
                    if isinstance(val, (VectorizedAccess, llc.VectorizedUpdate)):
                        new_idx_vars = tuple(
                            dim
                            if not isinstance(dim, Var) or dim.name != loop_stack[-1].counter.name
                            else new_counter
                            for dim in val.idx_vars
                        )
                        new_vectorization = tuple(
                            vectorization if dim != monolithic_for.counter else False
                            for dim, vectorization in zip(
                                new_idx_vars, val.vectorized_dims
                            )
                        )
                        val = dc.replace(
                            val,
                            idx_vars=new_idx_vars,
                            vectorized_dims=new_vectorization,
                        )
                        setattr(stmt, field.name, val)
                    unvectorize_loop_dim(val)

        for orig_var, lifted in lifted_vars.items():
            monolithic_for = util.replace_pattern(monolithic_for, orig_var, lifted)
        monolithic_for = util.replace_pattern(
            monolithic_for, loop_stack[-1].counter, monolithic_for.counter
        )
        unvectorize_loop_dim(monolithic_for)
        # For each phi node in the loop, update the true branch of that node to use the previous iteration's value
        for phi in monolithic_for.body:
            if isinstance(phi, llc.Phi):
                phi.rhs_true = util.replace_pattern(
                    phi.rhs_true,
                    monolithic_for.counter,
                    llc.BinOp(
                        monolithic_for.counter,
                        llc.BinOpKind.SUB,
                        llc.Constant(1, DataType.INT),
                    ),
                )
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
        elif isinstance(stmt, llc.VectorizedUpdate):
            return any(
                uses_loop_counter(item)
                for item, vectorized in zip(stmt.idx_vars, stmt.vectorized_dims)
                if not vectorized
            ) or uses_loop_counter(stmt.value)
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

                if isinstance(stmt.rhs, LiftExpr):
                    rhs_dim_sizes = [bound for _var, bound in stmt.rhs.dims]
                    rhs_vectorized_dims = [False] * len(rhs_dim_sizes)
                    rhs_idx_vars = [var for var, _bound in stmt.rhs.dims]
                else:
                    rhs_dim_sizes = []
                    rhs_vectorized_dims = []
                    rhs_idx_vars = []

                lifted_access = VectorizedAccess(
                    new_var,
                    dim_sizes=tuple(rhs_dim_sizes + [loop_stack[-1].bound_high]),
                    vectorized_dims=tuple(rhs_vectorized_dims + [True]),
                    idx_vars=tuple(rhs_idx_vars + [loop_stack[-1].counter]),
                )

                return {orig_var: (llc.Assign(new_var, new_rhs), lifted_access)}
            else:
                return {}
        elif isinstance(stmt, llc.For):
            return {
                var: assign
                for substmt in stmt.body
                for var, assign in lift_vars(substmt).items()
            }
        elif isinstance(stmt, (llc.Phi, llc.Return)):
            return {}
        else:
            assert_never(stmt)

    def ordering(
        s1: Union[llc.Statement, list[llc.Statement]],
        s2: Union[llc.Statement, list[llc.Statement]],
    ) -> int:
        # If s1 is a closure
        if isinstance(s1, list):
            # If s2 is a closure
            if isinstance(s2, list):
                orderings = set(ordering(ss1, s2) for ss1 in s1)
                orderings.discard(0)
                if len(orderings) == 2:
                    raise AssertionError(
                        "Two closures have been detected with circular dependencies"
                    )
                elif len(orderings) == 1:
                    return orderings.pop()
                else:
                    return 0
            # If s2 is a statement
            else:
                # If there is a dependency from s1 to s2, s1 must be placed first
                if any(dep_graph.has_same_level_path(ss1, s2) for ss1 in s1):
                    return -1
                # If there is a dependency from s2 to s1, then s2 must be placed first
                elif any(dep_graph.has_same_level_path(s2, ss1) for ss1 in s1):
                    return 1
                # Otherwise, they can be placed in any order
                else:
                    return 0
        # If s1 is a statement
        else:
            # If s2 is a closure
            if isinstance(s2, list):
                # If there is a dependency from s1 to s2, s1 must be placed first
                if any(dep_graph.has_same_level_path(s1, ss2) for ss2 in s2):
                    return -1
                # If there is a dependency from s2 to s1, then s2 must be placed first
                elif any(dep_graph.has_same_level_path(ss2, s1) for ss2 in s2):
                    return 1
                # Otherwise, they can be placed in any order
                else:
                    return 0
            # If s2 is a statement
            else:
                # If there is a dependency from s1 to s2, s1 must be placed first
                if dep_graph.has_same_level_path(s1, s2):
                    return -1
                # If there is a dependency from s2 to s1, then s2 must be placed first
                elif dep_graph.has_same_level_path(s2, s1):
                    return 1
                # Otherwise, they can be placed in any order
                else:
                    return 0

    stmts_and_closures: list[
        Union[llc.Statement, list[llc.Statement]]
    ] = vectorizeable + [
        closure for _, closure in closures  # type: ignore
    ]  # type: ignore

    stmts_and_closures = sorted(
        stmts_and_closures, key=functools.cmp_to_key(ordering)
    )  # Sort by index to retain def-use order

    # Generate output
    output: list[llc.Statement] = []
    lifted_arrs: dict[llc.Var, VectorizedAccess] = {}

    def lifted_stmt(stmt: llc.Statement) -> list[llc.Statement]:
        if uses_loop_counter(stmt):
            lifted = lift_vars(stmt)
            assignments: list[llc.Statement] = []
            for orig_var, val in lifted.items():
                assignment, lifted_access = val
                lifted_arrs[orig_var] = lifted_access
                assignments.append(assignment)
            return assignments
        elif (
            isinstance(stmt, llc.Assign)
            and isinstance(stmt.rhs, LiftExpr)
            and len(loop_stack) > 0
            and (loop_stack[-1].counter, loop_stack[-1].bound_high) not in stmt.rhs.dims
        ):
            new_dims = [(loop_stack[-1].counter, loop_stack[-1].bound_high)] + list(
                stmt.rhs.dims
            )
            new_rhs = LiftExpr(
                stmt.rhs.expr,
                tuple(new_dims),
            )
            return [dc.replace(stmt, rhs=new_rhs)]
        else:
            return [stmt]

    phi_renames = {}

    for i in range(len(stmts_and_closures)):
        if isinstance(stmts_and_closures[i], list):
            closure = cast(list, stmts_and_closures[i])
            closure_phis = [
                phi for phi in closure if isinstance(phi, llc.Phi) and not phi.removed
            ]

            # Update vectorizable statements before this point
            for phi in closure_phis:
                output = util.replace_pattern(output, phi.lhs, phi.rhs_false)

            # If every phi node in this closure is targetless, then we can
            # vectorize all statements in the closure
            if all(phi.targetless for phi in closure_phis):
                for stmt in closure:
                    # Phi nodes aren't removed (yet) since we may need to rename
                    # variables on other levels of the loop nest.  For now,
                    # just keep track of the fact that they need to be renamed.
                    if isinstance(stmt, llc.Phi):
                        lhs_var = stmt.lhs
                        if isinstance(lhs_var, llc.VectorizedAccess):
                            lhs_var = lhs_var.array

                        rhs_var = stmt.rhs_true
                        if isinstance(rhs_var, llc.VectorizedAccess):
                            rhs_var = rhs_var.array

                        phi_renames[lhs_var] = rhs_var
                        output.append(dc.replace(stmt, removed=True))
                    else:
                        for phi in closure_phis:
                            lhs_var = phi.lhs
                            if isinstance(lhs_var, llc.VectorizedAccess):
                                lhs_var = lhs_var.array

                            rhs_var = phi.rhs_false
                            if isinstance(rhs_var, llc.VectorizedAccess):
                                rhs_var = rhs_var.array

                            stmt = _replace_in_rhs(stmt, lhs_var, rhs_var)
                        output.extend(lifted_stmt(stmt))
            else:
                output.append(generate_monolithic_for(closure, lifted_arrs))
        else:
            statements = lifted_stmt(cast(llc.Statement, stmts_and_closures[i]))
            for statement in statements:
                for orig_var, lifted in lifted_arrs.items():
                    statement = util.replace_pattern(statement, orig_var, lifted)
                output.append(statement)

    return output, phi_renames


def clean_phi_renames(
    stmts: list[llc.Statement], phi_renames: dict[llc.Var, llc.Var]
) -> list[llc.Statement]:
    cleaned_stmts: list[llc.Statement] = []
    for stmt in stmts:
        # If this phi node is being marked for removal, do not add it to the clean statements
        if isinstance(stmt, llc.Phi) and stmt.removed:
            pass

        # If this is a for loop, we must recurse into it to keep track of removed
        # phi nodes inside the loop
        elif isinstance(stmt, llc.For):
            new_body = clean_phi_renames(stmt.body, phi_renames)
            cleaned_stmts.append(dc.replace(stmt, body=new_body))

        # Otherwise, add the statement to the cleaned output after replacing
        # variables with their renamed versions
        else:
            clean_stmt = stmt
            for orig_var, renamed_var in phi_renames.items():
                clean_stmt = util.replace_pattern(clean_stmt, orig_var, renamed_var)
            cleaned_stmts.append(clean_stmt)

    return cleaned_stmts


def basic_vectorization_phase_1(
    function: llc.Function, type_env: TypeEnv
) -> tuple[llc.Function, DepGraph]:
    dep_graph = DepGraph(function)
    tmp_var_gen = TempVarGenerator(dep_graph)

    before_func, body, after_func = _basic_vectorization_phase_1(
        function.body, dep_graph, type_env, tmp_var_gen
    )
    assert not before_func
    assert not after_func

    function = llc.Function(
        name=function.name,
        parameters=function.parameters,
        body=body,
        return_type=function.return_type,
    )

    _finalize_drop_dims(function.body, DepGraph(function))

    # Optimistically vectorize all new arrays
    _assign_vectorized_accesses(function, DepGraph(function))

    return function, DepGraph(function)


def basic_vectorization_phase_2(
    function: llc.Function,
) -> tuple[llc.Function, DepGraph]:
    loop_depth = _find_loop_depth(function.body) + 1

    phi_renames = {}

    for depth in reversed(range(loop_depth)):
        dep_graph = DepGraph(function)
        tmp_var_gen = TempVarGenerator(dep_graph)

        body, local_phi_renames = _basic_vectorization_phase_2(
            function.body, dep_graph, tmp_var_gen, depth
        )

        function = llc.Function(
            name=function.name,
            parameters=function.parameters,
            body=body,
            return_type=function.return_type,
        )

        phi_renames.update(local_phi_renames)

        for orig_var, new_var in phi_renames.items():
            if new_var in phi_renames:
                phi_renames[orig_var] = phi_renames[new_var]

    # Now that we've restructured the fuction based on phi closures, we need to clean up
    # the phi nodes which are marked for removal
    final_body = clean_phi_renames(function.body, phi_renames)
    function = llc.Function(
        name=function.name,
        parameters=function.parameters,
        body=final_body,
        return_type=function.return_type,
    )

    # Optimistically vectorize all new arrays
    _assign_vectorized_accesses(function, DepGraph(function))

    return (function, DepGraph(function))
