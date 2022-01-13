def max_sum_between_syms(Seq: shared[list[std::uint32_t]], N: plaintext[std::uint32_t], Sym: shared[std::uint32_t]):
    max_sum = 0
    current_sum = 0
    for i: plaintext[int] in range(0, N):
        if not (Seq[i] == Sym):
            current_sum = (current_sum + Seq[i])
        else:
            current_sum = 0
        if (current_sum > max_sum):
            max_sum = current_sum
    return max_sum
