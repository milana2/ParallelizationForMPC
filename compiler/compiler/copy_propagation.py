from .type_analysis import type_check
from .util import replace_pattern
from .dep_graph import DepGraph
from .loop_linear_code import (
    Function,
    Statement,
    Assign,
    TypeEnv,
    Var,
    Phi,
    For,
    Return,
    VectorizedAccess,
)

from typing import Optional
import dataclasses as dc


def _modify_stmts(
    stmts: list[Statement],
    changes: dict[Statement, Optional[Statement]],
) -> list[Statement]:
    ret = []
    for stmt in stmts:
        if stmt in changes and changes[stmt] is None:
            continue
        stmt = changes.get(stmt) or stmt
        if isinstance(stmt, For):
            stmt = dc.replace(stmt, body=_modify_stmts(stmt.body, changes))
        ret.append(stmt)
    return ret


def copy_propagation(
    func: Function, dep_graph: DepGraph, type_env: TypeEnv
) -> tuple[Function, DepGraph, TypeEnv]:
    changes: dict[Statement, Optional[Statement]] = dict()
    _copy_propagation_stmts(dep_graph, type_env, changes)
    func = dc.replace(func, body=_modify_stmts(func.body, changes))
    dep_graph = DepGraph(func)
    func, type_env = type_check(func, dep_graph)
    return func, dep_graph, type_env


def _copy_propagation_stmts(
    dep_graph: DepGraph,
    type_env: TypeEnv,
    changes: dict[Statement, Optional[Statement]],
) -> None:
    for old_var in type_env.keys():
        new_var = None
        def_ = dep_graph.var_to_assignment[old_var]
        while isinstance(def_, Assign) and isinstance(
            def_.rhs, (Var, VectorizedAccess)
        ):
            changes[def_] = None
            new_var = (
                def_.rhs.array if isinstance(def_.rhs, VectorizedAccess) else def_.rhs
            )
            def_ = dep_graph.var_to_assignment[new_var]
        if new_var is not None:
            for use in dep_graph.get_uses(old_var):
                if isinstance(use, For):
                    continue
                assert isinstance(use, (Phi, Assign, Return))
                changes[use] = replace_pattern(changes.get(use, use), old_var, new_var)
