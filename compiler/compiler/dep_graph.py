from typing import NewType, Union

from .util import assert_never
from . import loop_linear_code as llc


PhiOrAssign = Union[llc.Phi, llc.Assign]
DepGraph = NewType("DepGraph", dict[PhiOrAssign, list[PhiOrAssign]])


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
    assignments: list[PhiOrAssign] = []

    # TODO: Handle parameters

    def add_assignments(statements: list[llc.Statement]):
        for statement in statements:
            if isinstance(statement, llc.Phi) or isinstance(statement, llc.Assign):
                assignments.append(statement)
            elif isinstance(statement, llc.For):
                add_assignments(statement.body)
            else:
                assert_never(statement)

    add_assignments(function.body)

    var_to_assignment: dict[llc.Var, PhiOrAssign] = dict()

    for assignment in assignments:
        # This should be true if the SSA renaming is correct
        assert assignment.lhs not in var_to_assignment

        var_to_assignment[assignment.lhs] = assignment

    result = DepGraph(dict())

    for assignment in assignments:
        result[assignment] = []

    for assignment in assignments:
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
                result[var_def].append(assignment)

    # TODO: Handle return value

    return result
