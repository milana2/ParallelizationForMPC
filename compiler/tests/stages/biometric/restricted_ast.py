def biometric(C: shared[list[std::uint32_t]], D: plaintext[std::uint32_t], S: shared[list[std::uint32_t]], N: plaintext[std::uint32_t]):
    min_sum = 10000
    min_index = - 1
    for i: plaintext[int] in range(0, N):
        sum = 0
        for j: plaintext[int] in range(0, D):
            d = (S[((i * D) + j)] - C[j])
            p = (d * d)
            sum = (sum + p)
        if (sum < min_sum):
            min_sum = sum
            min_index = i
    return (min_sum, min_index)
