def count_102(Seq: shared[list[std::uint32_t]], N: plaintext[std::uint32_t], Syms: shared[list[std::uint32_t]]):
    s0 = False
    c = 0
    for i: plaintext[int] in range(0, N):
        if (s0 and (Seq[i] == Syms[2])):
            c = (c + 1)
        s0 = ((Seq[i] == Syms[1]) or (s0 and (Seq[i] == Syms[0])))
    return c
