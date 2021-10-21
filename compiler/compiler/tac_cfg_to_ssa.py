"""
Tools for converting from a three-address code control flow graph
to static single assignment form
"""

from collections import Counter

import networkx

import tac_cfg
import ssa


def _compute_blocks_setting_vars(
    function: ssa.Function,
) -> dict[ssa.AssignLHS, set[ssa.Block]]:

    result: dict[ssa.AssignLHS, set[ssa.Block]] = dict()

    for block in function.body.nodes:
        block: ssa.Block = block
        for assignment in block.assignments:
            var = assignment.lhs
            try:
                result[var].add(block)
            except KeyError:
                result[var] = set()

    return result


def _tac_cfg_to_ssa_struct(tac_cfg_function: tac_cfg.Function) -> ssa.Function:
    """
    Convert a `tac_cfg.Function` to an `ssa.Function` without
    trying to enforce any SSA properties.
    The output has no Phi-functions and may assign
    to the same variable multiple times.
    """

    cfg = networkx.DiGraph()
    mapping: dict[tac_cfg.Block, ssa.Block] = dict()

    for tac_cfg_block in tac_cfg_function.body.nodes:
        tac_cfg_block: tac_cfg.Block = tac_cfg_block
        ssa_block = ssa.Block(
            phi_functions=[],
            assignments=tac_cfg_block.assignments,
            terminator=tac_cfg_block.terminator,
        )
        cfg.add_node(ssa_block)
        mapping[tac_cfg_block] = ssa_block

    for source_block, dest_block, branch_kind in tac_cfg_function.body.edges(
        data="branch_kind"
    ):
        source_block: tac_cfg.Block = source_block
        dest_block: tac_cfg.Block = dest_block
        branch_kind: tac_cfg.BranchKind = branch_kind
        branch_kind: ssa.BranchKind = branch_kind
        cfg.add_edge(
            u_of_edge=mapping[source_block],
            v_of_edge=mapping[dest_block],
            branch_kind=branch_kind,
        )

    return ssa.Function(
        parameters=tac_cfg_function.parameters,
        body=cfg,
        entry_block=mapping[tac_cfg_function.entry_block],
        exit_block=mapping[tac_cfg_function.exit_block],
    )


def tac_cfg_to_ssa(tac_cfg_function: tac_cfg.Function) -> ssa.Function:
    result = _tac_cfg_to_ssa_struct(tac_cfg_function)

    dominance_frontiers: dict[
        ssa.Block, set[ssa.Block]
    ] = networkx.algorithms.dominance_frontiers(G=result.body, start=result.entry_block)

    blocks_setting_vars = _compute_blocks_setting_vars(result)

    # Place Phi-functions

    iter_count = 0
    has_already: Counter[ssa.Block] = Counter()
    work: Counter[ssa.Block] = Counter()
    W: set[ssa.Block] = set()

    for V in blocks_setting_vars.keys():
        iter_count += 1

        for X in blocks_setting_vars[V]:
            work[X] = iter_count
            W.add(X)

        while W != set():
            X = W.pop()
            for Y in dominance_frontiers[X]:
                Y: ssa.Block = Y
                if has_already[Y] < iter_count:
                    Y.phi_functions.append(
                        ssa.Phi(target_var=V, left_branch_var=V, right_branch_var=V)
                    )
                    has_already[Y] = iter_count
                    if work[Y] < iter_count:
                        work[Y] = iter_count
                        W.add(Y)

    return result
