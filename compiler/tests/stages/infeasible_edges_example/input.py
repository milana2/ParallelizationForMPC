def foo(
    A: shared[list[int]],
    B: shared[list[int]],
    C: shared[list[int]],
    D: shared[list[int]],
    N: int,
) -> tuple[shared[list[int]], shared[list[int]], shared[list[int]], shared[list[int]]]:
    for i in range(N):
        A[i] = B[i] + 10
        B[i] = A[i] * D[i - 1]
        C[i] = A[i] * D[i - 1]
        D[i] = B[i] * C[i]
    return (A, B, C, D)
