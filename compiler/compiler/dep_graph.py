from copy import copy
from enum import Enum
from typing import Iterator, Union, cast
from dataclasses import dataclass

import networkx

from .tac_cfg import DropDim, LiftExpr

from .util import assert_never
from . import loop_linear_code as llc


@dataclass(frozen=True)
class DepParameter:
    var: llc.Var

    def __str__(self) -> str:
        return f"parameter {self.var}"

    @property
    def lhs(self) -> llc.Var:
        return self.var


DepNode = Union[llc.Phi, llc.Assign, llc.For, llc.Return, DepParameter]


class EdgeKind(Enum):
    SAME_LEVEL = "same-level"
    OUTER_TO_INNER = "outer-to-inner"
    INNER_TO_OUTER = "inner-to-outer"


class DepGraph:
    def_use_graph: networkx.DiGraph
    enclosing_loops: dict[DepNode, list[llc.For]]
    var_to_assignment: dict[llc.Var, DepNode]

    def __init__(self, function: llc.Function) -> None:
        # Store all assignments and their enclosing loops.
        all_assignments: list[tuple[DepNode, list[llc.For]]] = []

        for param in function.parameters:
            all_assignments.append((DepParameter(param.var), []))

        def add_assignments(
            statements: list[llc.Statement], enclosing_loops: list[llc.For]
        ):
            for statement in statements:
                if isinstance(
                    statement,
                    (llc.Phi, llc.Assign, llc.Return),
                ):
                    all_assignments.append((statement, copy(enclosing_loops)))
                elif isinstance(statement, llc.For):
                    loop = statement
                    # Loops are considered to be inside themselves here,
                    # so that loop index accesses inside the loop can be same-level
                    all_assignments.append((loop, enclosing_loops + [loop]))
                    add_assignments(loop.body, enclosing_loops + [loop])
                elif isinstance(statement, llc.Return):
                    all_assignments.append((statement, copy(enclosing_loops)))
                else:
                    assert_never(statement)

        add_assignments(function.body, [])

        self.var_to_assignment: dict[llc.Var, DepNode] = dict()

        for assignment, _ in all_assignments:
            # Return statements aren't actually assignments, but they do use variables.
            # Since they don't have an lhs, we can skip them here.
            if isinstance(assignment, llc.Return):
                continue

            lhs = assignment.lhs
            if isinstance(lhs, llc.VectorizedAccess):
                lhs = lhs.array

            # This should be true if the SSA renaming is correct
            assert lhs not in self.var_to_assignment

            self.var_to_assignment[lhs] = assignment

        self.def_use_graph = networkx.DiGraph()
        for assignment, _ in all_assignments:
            self.def_use_graph.add_node(assignment)

        self.enclosing_loops = dict()
        for assignment, enclosing_loops in all_assignments:
            self.enclosing_loops[assignment] = enclosing_loops

        for assignment, _ in all_assignments:

            def collect_rhs(stmt: DepNode) -> list[llc.AssignRHS]:
                if isinstance(stmt, llc.Phi):
                    return cast(list[llc.AssignRHS], stmt.rhs_vars())
                elif isinstance(stmt, llc.Assign):
                    return [stmt.rhs]
                elif isinstance(stmt, DepParameter):
                    return [stmt.var]
                elif isinstance(stmt, llc.For):
                    if stmt.is_monolithic:
                        return [
                            used_var
                            for substmt in stmt.body
                            for used_var in collect_rhs(substmt)
                        ]
                    else:
                        return []
                elif isinstance(stmt, llc.Return):
                    return [stmt.value]
                else:
                    assert_never(stmt)

            lhss = [
                var
                for expr in collect_rhs(assignment)
                for var in llc.assign_rhs_accessed_vars(expr)
            ]

            for lhs in lhss:
                if isinstance(lhs, llc.VectorizedAccess):
                    lhs = lhs.array

                try:
                    var_def = self.var_to_assignment[lhs]
                except KeyError:
                    pass
                else:
                    self.def_use_graph.add_edge(var_def, assignment)

    def __str__(self) -> str:
        nodes = "\n".join([f"    {node}" for node in self.def_use_graph.nodes])
        edges = [(f"    {u}  →  {v}", u, v) for u, v in self.def_use_graph.edges]
        forward_edges = "\n".join(
            [s for s, u, v in edges if not self.is_back_edge(u, v)]
        )
        back_edges = "\n".join([s for s, u, v in edges if self.is_back_edge(u, v)])
        return (
            f"Nodes:\n{nodes}\n"
            + f"Forward edges:\n{forward_edges}\n"
            + f"Back edges:\n{back_edges}"
        ).strip()

    def edges(self) -> Iterator[tuple[DepNode, DepNode]]:
        return self.def_use_graph.edges()

    def is_back_edge(self, def_statement: DepNode, use_statement: DepNode) -> bool:
        return (
            self.def_use_graph.has_edge(def_statement, use_statement)
            and isinstance(use_statement, llc.Phi)
            and self.enclosing_loops[use_statement]
            == self.enclosing_loops[def_statement][
                : len(self.enclosing_loops[use_statement])
            ]
        )

    def edge_kind(self, def_stmt: DepNode, use_stmt: DepNode) -> EdgeKind:
        assert self.def_use_graph.has_edge(def_stmt, use_stmt)
        def_level = len(
            [loop for loop in self.enclosing_loops[def_stmt] if not loop.is_monolithic]
        )
        use_level = len(
            [loop for loop in self.enclosing_loops[use_stmt] if not loop.is_monolithic]
        )
        if def_level == use_level:
            return EdgeKind.SAME_LEVEL
        elif def_level < use_level:
            return EdgeKind.OUTER_TO_INNER
        else:
            return EdgeKind.INNER_TO_OUTER

    def has_same_level_path(
        self, src: DepNode, dest: DepNode, visited: set[DepNode] = set()
    ) -> bool:
        if src == dest:
            return True
        else:
            return any(
                self.has_same_level_path(use_stmt, dest, visited | {src})
                and self.edge_kind(src, use_stmt) == EdgeKind.SAME_LEVEL
                for use_stmt in self.def_use_graph.successors(src)
                if use_stmt not in visited
            )
