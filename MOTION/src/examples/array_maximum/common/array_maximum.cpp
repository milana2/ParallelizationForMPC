// MIT License
//
// Copyright (c) 2021 Arianne Roselina Prananto
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

#include "array_maximum.h"

#include <fstream>
#include <span>
#include "protocols/arithmetic_gmw/arithmetic_gmw_wire.h"
#include "protocols/bmr/bmr_wire.h"
#include "protocols/boolean_gmw/boolean_gmw_wire.h"
#include "secure_type/secure_unsigned_integer.h"
#include "statistics/analysis.h"
#include "statistics/run_time_statistics.h"
#include "utility/config.h"

/**
 * Constructs the inner product of the two given inputs.
 */
encrypto::motion::SecureUnsignedInteger CreateArrayMaximumCircuit(
    std::vector<encrypto::motion::SecureUnsignedInteger> a,
    std::vector<encrypto::motion::SecureUnsignedInteger> b) {
  encrypto::motion::SecureUnsignedInteger max_val = a[0];
  for (std::size_t i = 1; i < a.size(); i++) {
    auto cmp = max_val > a[i];
    max_val = cmp.Mux(max_val.Get(), a[i].Get());
  }

  for (std::size_t i = 0; i < b.size(); i++) {
    auto cmp = max_val > b[i];
    max_val = cmp.Mux(max_val.Get(), b[i].Get());
  }

  return max_val;
}

encrypto::motion::RunTimeStatistics EvaluateProtocol(
    encrypto::motion::PartyPointer& party, encrypto::motion::MpcProtocol protocol,
    std::span<const std::uint32_t> input_command_line, const std::string& input_file_path,
    bool print_output) {
  std::array<std::vector<encrypto::motion::SecureUnsignedInteger>, 2> shared_input;
  std::vector<std::vector<std::uint32_t>> input;

  // Checks if there is no input from command line.
  if (input_command_line.empty()) {
    // Takes input from file, path is given in input_file_path.
    for (const auto& v : GetFileInput(input_file_path)) {
      input.emplace_back(1, v);
    }
  } else {
    for (const auto& v : input_command_line) {
      input.emplace_back(1, v);
    }
  }

  /* Assigns input to its party using the given protocol.
   * The same input will be used as a dummy input for the other party, but only the party with the
   * same id will really set the input.
   * */
  switch (protocol) {
    case encrypto::motion::MpcProtocol::kBooleanGmw: {
      for (std::size_t i = 0; i < input.size(); i++) {
        shared_input[0].push_back(party->In<encrypto::motion::MpcProtocol::kBooleanGmw>(
            encrypto::motion::ToInput(input[i]), 0));
        shared_input[1].push_back(party->In<encrypto::motion::MpcProtocol::kBooleanGmw>(
            encrypto::motion::ToInput(input[i]), 1));
      }
      break;
    }
    case encrypto::motion::MpcProtocol::kBmr: {
      for (std::size_t i = 0; i < input.size(); i++) {
        shared_input[0].push_back(
            party->In<encrypto::motion::MpcProtocol::kBmr>(encrypto::motion::ToInput(input[i]), 0));
        shared_input[1].push_back(
            party->In<encrypto::motion::MpcProtocol::kBmr>(encrypto::motion::ToInput(input[i]), 1));
      }
      break;
    }
    default:
      throw std::invalid_argument("Invalid MPC protocol");
  }

  encrypto::motion::SecureUnsignedInteger output =
      CreateArrayMaximumCircuit(shared_input[0], shared_input[1]);

  // Constructs an output gate for the output.
  output = output.Out();

  party->Run();

  // Converts the output to an integer.
  auto result = output.As<std::uint32_t>();

  if (print_output) std::cout << "Result = " << result << std::endl;

  party->Finish();

  const auto& statistics = party->GetBackend()->GetRunTimeStatistics();
  return statistics.front();
}

/**
 * Takes input as vector of integers from file in path.
 */
std::vector<std::uint32_t> GetFileInput(const std::string& path) {
  std::ifstream infile;
  std::vector<std::uint32_t> input;
  std::uint32_t n;

  infile.open(path);
  if (!infile.is_open()) throw std::runtime_error("Could not open InnerProduct file");

  while (infile >> n) input.push_back(n);
  infile.close();
  return input;
}
