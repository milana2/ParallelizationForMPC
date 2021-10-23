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
encrypto::motion::SecureUnsignedInteger CreateArrayMaximumCircuitUnsimd(
    std::vector<encrypto::motion::SecureUnsignedInteger> A,
    std::vector<encrypto::motion::SecureUnsignedInteger> B) {
  // All of B's values into A
  std::copy(B.begin(), B.end(), std::back_inserter(A));

  encrypto::motion::SecureUnsignedInteger max_val = A[0];
  for (std::size_t i = 1; i < A.size(); i++) {
    auto cmp = max_val > A[i];
    max_val = cmp.Mux(max_val.Get(), A[i].Get());
  }

  return max_val;
}

encrypto::motion::SecureUnsignedInteger CreateArrayMaximumCircuitSimd(
    std::vector<encrypto::motion::SecureUnsignedInteger> A,
    std::vector<encrypto::motion::SecureUnsignedInteger> B) {
  // All of B's values into A
  std::copy(B.begin(), B.end(), std::back_inserter(A));

  while (A.size() > 1) {
    std::vector<encrypto::motion::SecureUnsignedInteger> firstHalf(A.begin(),
                                                                   A.begin() + A.size() / 2);
    std::vector<encrypto::motion::SecureUnsignedInteger> secondHalf(A.begin() + A.size() / 2,
                                                                    A.end());

    auto firstHalfSimd = encrypto::motion::SecureUnsignedInteger::Simdify(firstHalf);
    auto secondHalfSimd = encrypto::motion::SecureUnsignedInteger::Simdify(secondHalf);

    auto C = firstHalfSimd > secondHalfSimd;

    auto A_unsimd = C.Mux(firstHalfSimd.Get(), secondHalfSimd.Get()).Unsimdify();

    // A_unsimd is a vector of ShareWrappers, which for whatever reason cannot
    // be converted to a vector of SecureUnsignedIntegers (even though an individual
    // ShareWrapper can be converted to a SecureUnsignedInteger)...
    A.resize(A_unsimd.size());
    for (size_t i = 0; i < A.size(); i++) {
      A[i] = A_unsimd[i];
    }
  }

  return A[0];
}

encrypto::motion::RunTimeStatistics EvaluateProtocol(
    encrypto::motion::PartyPointer& party, encrypto::motion::MpcProtocol protocol,
    std::span<const std::uint32_t> input_command_line, const std::string& input_file_path,
    bool print_output, bool divide_and_conquer) {
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

  encrypto::motion::SecureUnsignedInteger output;
  if (!divide_and_conquer) {
    output = CreateArrayMaximumCircuitUnsimd(shared_input[0], shared_input[1]);
  } else {
    output = CreateArrayMaximumCircuitSimd(shared_input[0], shared_input[1]);
  }

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
