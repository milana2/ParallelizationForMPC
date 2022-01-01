from typing import Iterator, Union

import networkx  # type: ignore

from .util import assert_never
from . import loop_linear_code as llc


PhiOrAssign = Union[llc.Phi, llc.Assign]


class DepGraph:
    def_use_graph: networkx.DiGraph
    enclosing_loops: dict[PhiOrAssign, list[llc.For]]

    def __init__(self, function: llc.Function) -> None:
        # Store all assignments and their enclosing loops.
        all_assignments: list[tuple[PhiOrAssign, list[llc.For]]] = []

        # TODO: Handle parameters

        def add_assignments(
            statements: list[llc.Statement], enclosing_loops: list[llc.For]
        ):
            for statement in statements:
                if isinstance(statement, (llc.Phi, llc.Assign)):
                    all_assignments.append((statement, enclosing_loops))
                elif isinstance(statement, llc.For):
                    loop = statement
                    add_assignments(loop.body, enclosing_loops + [loop])
                else:
                    assert_never(statement)

        add_assignments(function.body, [])

        var_to_assignment: dict[llc.Var, PhiOrAssign] = dict()

        for assignment, _ in all_assignments:
            lhs = assignment.lhs

            # This should be true if the SSA renaming is correct
            assert lhs not in var_to_assignment

            var_to_assignment[lhs] = assignment

        self.def_use_graph = networkx.DiGraph()
        for assignment, _ in all_assignments:
            self.def_use_graph.add_node(assignment)

        for assignment, _ in all_assignments:
            if isinstance(assignment, llc.Phi):
                lhss = assignment.rhs
            elif isinstance(assignment, llc.Assign):
                lhss = _vars_in_rhs(assignment.rhs)
            else:
                assert_never(assignment)

            for lhs in lhss:
                try:
                    var_def = var_to_assignment[lhs]
                except KeyError:
                    pass
                else:
                    self.def_use_graph.add_edge(var_def, assignment)

        self.enclosing_loops = dict()
        for assignment, enclosing_loops in all_assignments:
            self.enclosing_loops[assignment] = enclosing_loops

        # TODO: Handle return value

    def edges(self) -> Iterator[tuple[PhiOrAssign, PhiOrAssign]]:
        return self.def_use_graph.edges()

    def is_back_edge(
        self, def_statement: PhiOrAssign, use_statement: PhiOrAssign
    ) -> bool:
        return (
            self.def_use_graph.has_edge(def_statement, use_statement)
            and isinstance(use_statement, llc.Phi)
            and self.enclosing_loops[use_statement]
            == self.enclosing_loops[def_statement][
                : len(self.enclosing_loops[use_statement])
            ]
        )

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


def _vars_in_rhs(rhs: llc.AssignRHS) -> list[llc.Var]:
    if isinstance(rhs, llc.Var):
        return [rhs]
    elif isinstance(rhs, llc.Subscript):
        return [rhs.array]
    elif isinstance(rhs, llc.ConstantInt):
        return []
    elif isinstance(rhs, llc.BinOp):
        return _vars_in_rhs(rhs.left) + _vars_in_rhs(rhs.right)
    elif isinstance(rhs, llc.UnaryOp):
        return _vars_in_rhs(rhs.operand)
    elif isinstance(rhs, (llc.List, llc.Tuple)):
        return [lhs for rhs_item in rhs.items for lhs in _vars_in_rhs(rhs_item)]
    elif isinstance(rhs, llc.Mux):
        return [
            v
            for v in (rhs.condition, rhs.false_value, rhs.true_value)
            if isinstance(v, llc.Var)
        ]
    elif isinstance(rhs, llc.Update):
        return [rhs.array] + _vars_in_rhs(rhs.value)
    else:
        assert_never(rhs)
