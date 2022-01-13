def foo(A: plaintext[std::uint32_t], B: plaintext[std::uint32_t], C: plaintext[std::uint32_t], D: plaintext[std::uint32_t], N: plaintext[std::uint32_t]):
    for i: plaintext[int] in range(0, N):
        A[i] = (B[i] + 10)
        B[i] = (A[i] * D[(i - 1)])
        C[i] = (A[i] * D[(i - 1)])
        D[i] = (B[i] * C[i])
    return (A, B, C, D)
