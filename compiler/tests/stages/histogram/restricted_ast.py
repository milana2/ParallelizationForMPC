def histogram(A: shared[list[std::uint32_t]], B: shared[list[std::uint32_t]], N: plaintext[std::uint32_t], num_bins: plaintext[std::uint32_t]):
    result = []
    for i: plaintext[int] in range(0, num_bins):
        result = (result + [0])
    for i: plaintext[int] in range(0, num_bins):
        for j: plaintext[int] in range(0, N):
            if (A[j] == i):
                result[i] = (result[i] + B[j])
    return result
