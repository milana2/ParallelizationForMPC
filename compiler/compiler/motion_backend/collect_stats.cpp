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

bool is_local(const GatePointer &gate)
{
    return dynamic_cast<proto::boolean_gmw::XorGate *>(&*gate) ||
           dynamic_cast<proto::bmr::XorGate *>(&*gate) ||
           dynamic_cast<proto::boolean_gmw::InvGate *>(&*gate) ||
           dynamic_cast<proto::bmr::InvGate *>(&*gate) || dynamic_cast<SimdifyGate *>(&*gate) ||
           dynamic_cast<UnsimdifyGate *>(&*gate);
}

std::vector<std::int64_t> collect_children(const BackendPointer backend, const std::int64_t gate_id,
                                           std::unordered_set<std::int64_t> &seen_gates)
{
    std::vector<std::int64_t> children;

    const auto gate = backend->GetGate(gate_id);

    for (const auto &output_wire : gate->GetOutputWires()) {
        for (const auto &child_gate_id : output_wire->GetWaitingGatesIds()) {
            if (seen_gates.find(child_gate_id) != seen_gates.end()) {
                continue;
            }

            const auto child_gate = backend->GetGate(child_gate_id);
            if (is_local(child_gate)) {
                auto child_children = collect_children(backend, child_gate_id, seen_gates);

                children.insert(children.end(), child_children.begin(), child_children.end());
            } else {
                children.push_back(child_gate_id);
            }

            seen_gates.insert(child_gate_id);
        }
    }

    return children;
}

CircuitStats collect_stats(const BackendPointer backend)
{
    CircuitStats stats;
    std::unordered_set<std::int64_t> visited_gates;

    std::ofstream dot("circuit.dot");
    dot << "digraph circuit {" << std::endl;

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

        if (dynamic_cast<InputGate *>(&*gate)) {
            dot << gate_id << " [label=\"Input\"";
        } else if (dynamic_cast<OutputGate *>(&*gate)) {
            dot << gate_id << " [label=\"Output\"";
        } else if (dynamic_cast<proto::boolean_gmw::XorGate *>(&*gate) ||
                   dynamic_cast<proto::bmr::XorGate *>(&*gate)) {
            dot << gate_id << " [label=\"Xor\"";
        } else if (dynamic_cast<proto::boolean_gmw::InvGate *>(&*gate) ||
                   dynamic_cast<proto::bmr::InvGate *>(&*gate)) {
            dot << gate_id << " [label=\"Not\"";
        } else if (dynamic_cast<proto::boolean_gmw::AndGate *>(&*gate) ||
                   dynamic_cast<proto::bmr::AndGate *>(&*gate)) {
            dot << gate_id << " [label=\"And\"";
        } else if (dynamic_cast<proto::boolean_gmw::MuxGate *>(&*gate)) {
            dot << gate_id << " [label=\"Mux\"";
        } else if (dynamic_cast<SimdifyGate *>(&*gate)) {
            dot << gate_id << " [label=\"Simdify\"";
        } else if (dynamic_cast<UnsimdifyGate *>(&*gate)) {
            dot << gate_id << " [label=\"Unsimdify\"";
        } else {
            throw std::runtime_error("Unknown gate type");
        }

        if (is_local(gate)) {
            dot << ", fillcolor=\"red\", style=\"filled\"";
        }
        dot << "];" << std::endl;

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

        std::unordered_set<std::int64_t> visited_children;

        // Add all children to the queue
        for (const auto &output_wire : gate->GetOutputWires()) {
            for (const auto &child_gate_id : output_wire->GetWaitingGatesIds()) {
                if (visited_children.find(child_gate_id) == visited_children.end()) {
                    dot << gate_id << " -> " << child_gate_id << "[label=\""
                        << output_wire->GetNumberOfSimdValues() << "\"];" << std::endl;
                    queue.push(std::make_pair(output_wire, child_gate_id));
                    visited_children.insert(child_gate_id);
                }
            }
        }
    }
    dot << "}" << std::endl;

    std::queue<std::int64_t> write_queue;
    std::queue<std::int64_t> read_queue;
    for (const auto &gate : backend->GetInputGates()) {
        read_queue.push(gate->GetId());
    }

    stats.depth = 0;

    while (!read_queue.empty()) {
        ++stats.depth;

        std::unordered_set<std::int64_t> seen_gates;
        while (!read_queue.empty()) {
            const auto gate_id = read_queue.front();
            read_queue.pop();
            const auto gate = backend->GetGate(gate_id);

            if (dynamic_cast<OutputGate *>(&*gate)) {
                continue;
            }

            auto children = collect_children(backend, gate_id, seen_gates);

            for (const auto &child_gate_id : children) {
                write_queue.push(child_gate_id);
            }
        }
        std::swap(read_queue, write_queue);
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
