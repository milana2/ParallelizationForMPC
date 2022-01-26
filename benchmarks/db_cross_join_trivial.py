from UTIL import shared


def cross_join_trivial(
    A: shared[list[int]],
    Len_A: int,
    Att_A: int,
    B: shared[list[int]],
    Len_B: int,
    Att_B: int,
) -> shared[list[int]]:
    ret: list[int] = []

    Att = Att_A + Att_B - 1

    for i in range(0, Len_A * Len_B * Att + 1):
        ret = ret + [0]

    for i in range(0, Len_A):
        for j in range(0, Len_B):
            if A[i * Att_A] == B[j * Att_B]:
                ret[(i * Len_B + j) * Att] = A[i * Att_A]
                ret[(i * Len_B + j) * Att + 1] = A[i * Att_A + 1]
                ret[(i * Len_B + j) * Att + 2] = B[j * Att_B + 1]

    return ret
