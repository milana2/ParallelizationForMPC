#include "collect_stats.h"

#include "protocols/bmr/bmr_gate.h"
#include "protocols/boolean_gmw/boolean_gmw_gate.h"
#include "protocols/data_management/simdify_gate.h"
#include "protocols/data_management/unsimdify_gate.h"

#include <fstream>
#include <iostream>
#include <queue>
#include <stack>
#include <unordered_set>
#include <utility>

using namespace encrypto::motion;

CircuitStats collect_stats(const BackendPointer backend)
{
    CircuitStats stats;

    for (const GatePointer gate : backend->GetRegister()->GetGates()) {
        stats.num_gates++;
        if (dynamic_cast<InputGate *>(&*gate)) {
            stats.num_inputs++;
        }
        if (dynamic_cast<OutputGate *>(&*gate)) {
            stats.num_outputs++;
        }
        bool is_simd = true;
        for (const WirePointer wire : gate->GetOutputWires()) {
            if (wire->GetNumberOfSimdValues() <= 1) {
                is_simd = false;
                break;
            }
        }
        if (is_simd) {
            stats.num_simd_gates++;
        } else {
            stats.num_nonsimd_gates++;
        }
    }

    return stats;
}

std::ostream &operator<<(std::ostream &ostr, const CircuitStats &stats)
{
    ostr << "num_gates: " << stats.num_gates << std::endl;
    ostr << "num_inputs: " << stats.num_inputs << std::endl;
    ostr << "num_outputs: " << stats.num_outputs << std::endl;
    ostr << "num_simd_gates: " << stats.num_simd_gates << std::endl;
    ostr << "num_nonsimd_gates: " << stats.num_nonsimd_gates << std::endl;
    return ostr;
}
