def foo(A: shared[list[std::uint32_t]], B: shared[list[std::uint32_t]], C: shared[list[std::uint32_t]], D: shared[list[std::uint32_t]], N: plaintext[std::uint32_t]):
    for i: plaintext[int] in range(0, N):
        A[i] = (B[i] + 10)
        B[i] = (A[i] * D[(i - 1)])
        C[i] = (A[i] * D[(i - 1)])
        D[i] = (B[i] * C[i])
    return (A, B, C, D)
