def foo(A: plaintext[int], B: plaintext[int], C: plaintext[int], D: plaintext[int], N: plaintext[int]):
    for i: plaintext[int] in range(0, N):
        A[i] = (B[i] + 10)
        B[i] = (A[i] * D[(i - 1)])
        C[i] = (A[i] * D[(i - 1)])
        D[i] = (B[i] * C[i])
    return (A, B, C, D)
