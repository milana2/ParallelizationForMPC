def foo(D, N, C, C_sqr_sum, two_C, S, S_sqr_sum):
    differences = ([0] * D)
    for i in range(0, N):
        a_sqr_plus_b_sqr = (S_sqr_sum[i] + C_sqr_sum)
        two_a_b = 0
        for j in range(0, D):
            tmp = (S[((i * D) + j)] * two_C[j])
            two_a_b = (two_a_b + tmp)
        this_diff = (a_sqr_plus_b_sqr - two_a_b)
        differences[i] = this_diff
        min_diff = differences[0]
        min_index = 0
        for k in range(0, N):
            if (differences[k] < min_diff):
                min_diff = differences[k]
                min_index = k
    return [min_diff, min_index]
