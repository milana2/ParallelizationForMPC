#pragma once

#include <iostream>

#include "base/backend.h"

struct CircuitStats {
    std::size_t num_gates = 0;
    std::size_t num_inputs = 0;
    std::size_t num_outputs = 0;

    std::size_t num_simd_gates = 0;
    std::size_t num_nonsimd_gates = 0;
};

CircuitStats collect_stats(const encrypto::motion::BackendPointer backend);

std::ostream &operator<<(std::ostream &ostr, const CircuitStats &stats);
