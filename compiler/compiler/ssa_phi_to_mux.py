from . import ssa


def replace_phi_with_mux(result: ssa.Function) -> None:
    block: ssa.Block
    for block in result.body.nodes:
        if block.merge_condition is not None:
            mux_calls = []
            for phi in block.phi_functions:
                mux_calls.append(
                    ssa.Assign(
                        lhs=phi.lhs,
                        rhs=ssa.Mux(
                            condition=block.merge_condition.condition,
                            false_value=phi.rhs_false,
                            true_value=phi.rhs_true,
                        ),
                    )
                )
            block.phi_functions = []
            block.assignments = mux_calls + block.assignments
