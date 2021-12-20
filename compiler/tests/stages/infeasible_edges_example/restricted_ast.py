def foo(A: plaintext, B: plaintext, C: plaintext, D: plaintext, N: plaintext):
    for i: plaintext in range(0, N):
        A[i] = (B[i] + 10)
        B[i] = (A[i] * D[(i - 1)])
        C[i] = (A[i] * D[(i - 1)])
        D[i] = (B[i] * C[i])
    return (A, B, C, D)
