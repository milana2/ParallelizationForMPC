from typing import NewType, Optional, Union
from dataclasses import dataclass

from .util import assert_never
from . import loop_linear_code as llc


PhiOrAssign = Union[llc.Phi, llc.Assign]


@dataclass
class DepGraphUse:
    """
    Target node of edges of dependency graph

    * `assignment` - assignment where the variable is used
    * `enclosing_loop` - the innermost loop containing `assignment`,
      or `None` if the assignment is at the top level and not inside any loops
    """

    assignment: PhiOrAssign
    enclosing_loop: Optional[llc.For]


DepGraph = NewType("DepGraph", dict[PhiOrAssign, list[DepGraphUse]])


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
    elif isinstance(rhs, llc.List) or isinstance(rhs, llc.Tuple):
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


def compute_dep_graph(function: llc.Function) -> DepGraph:
    # Store all possible uses in def-use pairs.
    # This contains all assignments and their enclosing loops.
    possible_uses: list[DepGraphUse] = []

    # TODO: Handle parameters

    def add_assignments(
        statements: list[llc.Statement], enclosing_loop: Optional[llc.For]
    ):
        for statement in statements:
            if isinstance(statement, llc.Phi) or isinstance(statement, llc.Assign):
                possible_uses.append(
                    DepGraphUse(assignment=statement, enclosing_loop=enclosing_loop)
                )
            elif isinstance(statement, llc.For):
                add_assignments(statement.body, statement)
            else:
                assert_never(statement)

    add_assignments(function.body, None)

    var_to_assignment: dict[llc.Var, PhiOrAssign] = dict()

    for use in possible_uses:
        assignment = use.assignment
        lhs = assignment.lhs

        # This should be true if the SSA renaming is correct
        assert lhs not in var_to_assignment

        var_to_assignment[lhs] = assignment

    result = DepGraph(dict())

    for use in possible_uses:
        result[use.assignment] = []

    for use in possible_uses:
        assignment = use.assignment
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
                result[var_def].append(use)

    # TODO: Handle return value

    return result
