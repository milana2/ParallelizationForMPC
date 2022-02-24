from collections import defaultdict
from typing import Union
from dataclasses import dataclass

import networkx  # type: ignore

from .util import assert_never
from . import ssa


_Statement = Union[ssa.Phi, ssa.Assign, ssa.BlockTerminator]


@dataclass(frozen=True)
class _StatementBlock:
    statement: _Statement
    block: ssa.Block


def _accessed_vars(s: _StatementBlock) -> list[ssa.Var]:
    if isinstance(s.statement, ssa.Phi):
        return s.statement.rhs_vars()
    elif isinstance(s.statement, ssa.Assign):
        return ssa.assign_rhs_accessed_vars(s.statement.rhs)
    elif isinstance(s.statement, ssa.Jump):
        return []
    elif isinstance(s.statement, ssa.ConditionalJump):
        return [s.statement.condition]
    elif isinstance(s.statement, ssa.For):
        low = ssa.assign_rhs_accessed_vars(s.statement.bound_low)
        high = ssa.assign_rhs_accessed_vars(s.statement.bound_high)
        return low + high
    elif isinstance(s.statement, ssa.Return):
        return [s.statement.value]
    else:
        assert_never(s.statement)


def _compute_statements_setting_vars(
    function: ssa.Function,
) -> defaultdict[ssa.Var, set[_StatementBlock]]:
    result: defaultdict[ssa.Var, set[_StatementBlock]] = defaultdict(set)

    block: ssa.Block
    for block in function.body.nodes:

        assignments: list[Union[ssa.Phi, ssa.Assign, ssa.For]] = []
        for phi in block.phi_functions:
            assignments.append(phi)
        for a in block.assignments:
            assignments.append(a)
        if isinstance(block.terminator, ssa.For):
            assignments.append(block.terminator)

        for assignment in assignments:
            if isinstance(assignment, (ssa.Phi, ssa.Assign)):
                assert isinstance(
                    assignment.lhs, ssa.Var
                ), "VectorizedAccesses are not added until basic vectorization"
                var = assignment.lhs
            elif isinstance(assignment, ssa.For):
                var = assignment.counter
            else:
                assert_never(assignment)

            if var not in result:
                result[var] = set()

            result[var].add(_StatementBlock(statement=assignment, block=block))

    return result


def _definers(
    s: _StatementBlock,
    statements_setting_vars: defaultdict[ssa.Var, set[_StatementBlock]],
) -> set[_StatementBlock]:
    return {d for var in _accessed_vars(s) for d in statements_setting_vars[var]}


def _last(b: ssa.Block) -> _StatementBlock:
    assert b.terminator is not None
    return _StatementBlock(statement=b.terminator, block=b)


def dead_code_elim(function: ssa.Function) -> None:
    statements_setting_vars = _compute_statements_setting_vars(function)
    cd_1: dict[ssa.Block, set[ssa.Block]] = networkx.algorithms.dominance_frontiers(
        G=function.body.reverse(), start=function.exit_block
    )
    block: ssa.Block

    assert function.exit_block.terminator is not None
    pre_live: set[_StatementBlock] = {
        _StatementBlock(
            statement=function.exit_block.terminator, block=function.exit_block
        )
    }
    live = pre_live.copy()
    work_list = pre_live.copy()

    while len(work_list) != 0:
        s = work_list.pop()

        for d in _definers(s, statements_setting_vars):
            if d not in live:
                live.add(d)
                work_list.add(d)

        for block in cd_1[s.block]:
            if _last(block) not in live:
                live.add(_last(block))
                work_list.add(_last(block))

    for block in function.body.nodes:
        block.phi_functions = [
            s for s in block.phi_functions if _StatementBlock(s, block) in live
        ]
        block.assignments = [
            s for s in block.assignments if _StatementBlock(s, block) in live
        ]
