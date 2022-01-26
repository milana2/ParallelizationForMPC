from UTIL import shared


def cross_join(
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

    ret_idx = 0

    for i in range(0, Len_A):
        for j in range(0, Len_B):
            if A[i * Att_A] == B[j * Att_B]:
                ret[ret_idx * Att] = A[i * Att_A]
                ret[ret_idx * Att + 1] = A[i * Att_A + 1]
                ret[ret_idx * Att + 2] = B[j * Att_B + 1]
                ret_idx = ret_idx + 1

    return ret
