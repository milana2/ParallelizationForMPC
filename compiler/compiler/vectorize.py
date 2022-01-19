from compiler.restricted_ast import Assign
from . import loop_linear_code as llc
from .dep_graph import DepGraph, PhiOrAssign
from .util import assert_never

from dataclasses import dataclass
from typing import Iterable, Union, Optional

import z3  # type: ignore


@dataclass
class ArrayRead:
    subscript: llc.Subscript
    parent_loops: list[llc.For]


def _new_temp_var(dep_graph: DepGraph):
    nodes: Iterable[PhiOrAssign] = dep_graph.def_use_graph.nodes
    number = max([0 if isinstance(a.lhs.name, str) else a.lhs.name for a in nodes]) + 1
    return llc.Var(number, 0)


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
    if isinstance(rhs, (llc.Var, llc.Constant)):
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
        return left * right
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
        if isinstance(A_use, llc.Phi) and A_use.lhs.name == A_name:
            assert dep_graph.enclosing_loops[A_use][-1] == j
            A_defs: list[PhiOrAssign] = list(
                dep_graph.def_use_graph.predecessors(A_use)
            )
            for A_def in A_defs:
                assert A_def.lhs.name == A_name
                if dep_graph.is_back_edge(A_def, A_use):
                    dep_graph.def_use_graph.remove_edge(A_def, A_use)


def _prune_edges_from_loop(i: list[llc.For], j: llc.For, dep_graph: DepGraph) -> None:
    for A_def in _arrays_written_in_loop(j):
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
    A_def: PhiOrAssign
    [A_def] = [
        A_def for A_def in dep_graph.def_use_graph.predecessors(A_use) if A_def.lhs == A
    ]
    return (
        A_def.rhs.index
        if isinstance(A_def, llc.Assign) and isinstance(A_def.rhs, llc.Update)
        else None
    )


def _refine_array_mux_statement(
    statement: llc.Statement, dep_graph: DepGraph
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
                temp = _new_temp_var(dep_graph)
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
                body=_refine_array_mux_statements(statement.body, dep_graph),
            )
        ]
    else:
        return [statement]


def _refine_array_mux_statements(
    stmts: list[llc.Statement], dep_graph: DepGraph
) -> list[llc.Statement]:
    return [
        rstmt
        for stmt in stmts
        for rstmt in _refine_array_mux_statement(stmt, dep_graph)
    ]


def refine_array_mux(
    function: llc.Function, dep_graph: DepGraph
) -> tuple[llc.Function, DepGraph]:
    function = llc.Function(
        name=function.name,
        parameters=function.parameters,
        body=_refine_array_mux_statements(function.body, dep_graph),
        return_value=function.return_value,
        return_type=function.return_type,
    )
    dep_graph = DepGraph(function)
    return (function, dep_graph)
