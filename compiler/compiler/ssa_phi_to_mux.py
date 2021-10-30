from . import ssa


def replace_phi_with_mux(result: ssa.Function) -> None:
    for block in result.body.nodes:
        block: ssa.Block
        if block.merge_condition is not None:
            mux_calls = []
            for phi in block.phi_functions:
                [false_value, true_value] = phi.rhs
                mux_calls.append(
                    ssa.Assign(
                        lhs=phi.lhs,
                        rhs=ssa.Mux(
                            condition=block.merge_condition.condition,
                            false_value=false_value,
                            true_value=true_value,
                        ),
                    )
                )
            block.phi_functions = []
            block.assignments = mux_calls + block.assignments
