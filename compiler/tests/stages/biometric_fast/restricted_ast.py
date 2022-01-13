def biometric_matching_fast(D: plaintext[std::uint32_t], N: plaintext[std::uint32_t], C: shared[list[std::uint32_t]], C_sqr_sum: shared[std::uint32_t], two_C: shared[list[std::uint32_t]], S: shared[list[std::uint32_t]], S_sqr_sum: shared[list[std::uint32_t]]):
    differences = []
    for i: plaintext[int] in range(0, D):
        differences[i] = (differences + [0])
    for i: plaintext[int] in range(0, N):
        a_sqr_plus_b_sqr = (S_sqr_sum[i] + C_sqr_sum)
        two_a_b = 0
        for j: plaintext[int] in range(0, D):
            tmp = (S[((i * D) + j)] * two_C[j])
            two_a_b = (two_a_b + tmp)
        this_diff = (a_sqr_plus_b_sqr - two_a_b)
        differences[i] = this_diff
        min_diff = differences[0]
        min_index = 0
        for k: plaintext[int] in range(0, N):
            if (differences[k] < min_diff):
                min_diff = differences[k]
                min_index = k
    return (min_diff, min_index)
