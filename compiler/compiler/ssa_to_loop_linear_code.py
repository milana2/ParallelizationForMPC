from . import ssa
from . import loop_linear_code


def ssa_to_loop_linear_code(ssa_function: ssa.Function) -> loop_linear_code.Function:
    visited: set[ssa.Block] = set()
    merge_visited: set[ssa.Block] = set()

    def search(node: ssa.Block) -> list[loop_linear_code.Statement]:
        if node.merge_condition is not None and node not in merge_visited:
            merge_visited.add(node)
            return []

        visited.add(node)

        successors: list[tuple[ssa.BranchKind, ssa.Block]] = [
            (edge_label, successor)
            for (_, successor, edge_label) in ssa_function.body.out_edges(
                node, data="label"
            )
            if successor not in visited
        ]

        successors.sort(
            key=lambda s: {
                ssa.BranchKind.UNCONDITIONAL: 0,
                ssa.BranchKind.FALSE: 1,
                ssa.BranchKind.TRUE: 2,
            }[s[0]]
        )

        empty: list[loop_linear_code.Statement] = []  # Required for type checker
        return (
            empty
            + [a for a in node.assignments]
            + (
                (
                    empty
                    + [
                        loop_linear_code.For(
                            counter=node.terminator.counter,
                            bound_low=node.terminator.bound_low,
                            bound_high=node.terminator.bound_high,
                            body=empty
                            + [a for a in node.phi_functions]
                            + search(successors[1][1]),
                        )
                    ]
                    + search(successors[0][1])
                )
                if isinstance(node.terminator, ssa.For)
                else [a for _, successor in successors for a in search(successor)]
            )
        )

    assert isinstance(ssa_function.exit_block.terminator, ssa.Return)

    return loop_linear_code.Function(
        name=ssa_function.name,
        parameters=ssa_function.parameters,
        body=search(ssa_function.entry_block),
        return_value=ssa_function.exit_block.terminator.value,
        return_type=ssa_function.return_type,
    )
