def ip(A: shared[list[std::uint32_t]], B: shared[list[std::uint32_t]], N: plaintext[std::uint32_t]):
    sum = 0
    for i: plaintext[int] in range(0, N):
        temp = (A[i] * B[i])
        sum = (sum + temp)
    return sum
