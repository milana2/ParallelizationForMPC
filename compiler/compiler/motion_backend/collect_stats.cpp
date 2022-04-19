#include "collect_stats.h"

#include <iostream>
#include <queue>
#include <unordered_set>
#include <utility>
#include <stack>

using namespace encrypto::motion;

CircuitStats collect_stats(const BackendPointer backend)
{
    CircuitStats stats;
    std::unordered_set<std::int64_t> visited_gates;

    // Perform a breadth-first traversal of the circuit, collecting data as we go
    std::queue<std::pair<const WirePointer, const std::int64_t>> queue;
    for (const auto &inp : backend->GetInputGates()) {
        queue.push(std::make_pair(nullptr, inp->GetId()));
    }

    while (!queue.empty()) {
        const auto [wire, gate_id] = queue.front();
        queue.pop();

        // If we've already visited this gate, skip it
        if (visited_gates.find(gate_id) != visited_gates.end()) {
            continue;
        }
        visited_gates.insert(gate_id);

        const auto gate = backend->GetGate(gate_id);

        // Count the gate
        ++stats.num_gates;

        // If this is an input gate, increment the number of inputs
        if (dynamic_cast<InputGate *>(&*gate)) {
            ++stats.num_inputs;
        }

        // If this is an output gate, increment the number of outputs
        if (dynamic_cast<OutputGate *>(&*gate)) {
            ++stats.num_outputs;
        }

        // If this is not an input gate (i.e. there is a wire which leads into this gate),
        // determine if that wire is SIMD
        if (wire != nullptr) {
            if (wire->GetNumberOfSimdValues() > 1) {
                ++stats.num_simd_gates;
            } else {
                ++stats.num_nonsimd_gates;
            }
        }

        // Add all children to the queue
        for (const auto &output_wire : gate->GetOutputWires()) {
            for (const auto &child_gate_id : output_wire->GetWaitingGatesIds()) {
                queue.push(std::make_pair(output_wire, child_gate_id));
            }
        }
    }

    // depth first search to determine depth
    std::queue<std::int64_t> writeQueue;
    std::queue<std::int64_t> readQueue;
    for(const auto &gate : backend->GetInputGates()) {
        readQueue.push(gate->GetId());
    }

    stats.depth = 0;

    while(!readQueue.empty()) {
        ++stats.depth;

        std::unordered_set<std::int64_t> seen_gates;
        while(!readQueue.empty()) {
            const auto gate_id = readQueue.front();
            readQueue.pop();
            const auto gate = backend->GetGate(gate_id);

            if(dynamic_cast<OutputGate *>(&*gate)) {
                continue;
            }
                
            for (const auto &output_wire : gate->GetOutputWires()) {
                for (const auto &child_gate_id : output_wire->GetWaitingGatesIds()) {
                    if(seen_gates.find(child_gate_id) != seen_gates.end()) {
                        continue;
                    }
                    writeQueue.push(child_gate_id);
                    seen_gates.insert(child_gate_id);

                }
            }
        }
        std::swap(readQueue, writeQueue);
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
    ostr << "depth: " << stats.depth << std::endl;
    return ostr;
}
