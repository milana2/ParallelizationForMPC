def max_sum_between_syms(Seq: shared, N: plaintext, Sym: shared):
    max_sum = 0
    current_sum = 0
    for i: plaintext in range(0, N):
        if not (Seq[i] == Sym):
            current_sum = (current_sum + Seq[i])
        else:
            current_sum = 0
        if (current_sum > max_sum):
            max_sum = current_sum
    return max_sum
