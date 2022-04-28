def biometric_fast(D: plaintext[int], N: plaintext[int], C: shared[list[int; ?]], C_sqr_sum: shared[int], two_C: shared[list[int; ?]], S: shared[list[int; ?]], S_sqr_sum: shared[list[int; ?]], differences: shared[list[int; ?]]) -> tuple[shared[int], shared[int]]:
    min_index = 0
    for i: plaintext[int] in range(0, N):
        a_sqr_plus_b_sqr = (S_sqr_sum[i] + C_sqr_sum)
        two_a_b = 0
        for j: plaintext[int] in range(0, D):
            tmp = (S[((i * D) + j)] * two_C[j])
            two_a_b = (two_a_b + tmp)
        this_diff = (a_sqr_plus_b_sqr - two_a_b)
        differences[i] = this_diff
        min_index = 0
    min_diff = 99999
    for i: plaintext[int] in range(0, N):
        if (differences[i] < min_diff):
            min_diff = differences[i]
            min_index = i
    return (min_diff, min_index)
