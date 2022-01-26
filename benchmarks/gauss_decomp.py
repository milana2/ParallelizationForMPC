from UTIL import shared


def gauss_decomp(
    M: shared[list[int]], V: shared[list[int]], N: int
) -> shared[list[int]]:
    L: list[int] = []
    for i in range(0, N):
        for j in range(0, N):
            if i == j:
                L = L + [1]
            else:
                L = L + [0]

    for i in range(0, N):
        for k in range(i + 1, N):
            L[k * N + i] = M[k * N + 1] / M[i * N + i]
            for j in range(i, N):
                M[k * N + j] = M[k * N + j] - L[k * N + i] * M[i * N + j]
            V[k] = V[k] - L[k * N + i] * V[i]

    ret: list[int] = []
    for i in range(N):
        ret += [0]

    ret[N - 1] = V[N - 1] / M[(N - 1) * N + N - 1]

    # for (i=N-2; i>=0; i--)
    for i in range(N - 2, -1, -1):
        tmp = 0
        for j in range(i + 1, N):
            tmp = tmp + (ret[j] * M[i * N + j])
        ret[i] = (V[i] - tmp) / M[i * N + i]

    return ret
