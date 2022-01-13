def longest_1s(Seq: shared[list[std::uint32_t]], N: plaintext[std::uint32_t], Sym: shared[std::uint32_t]):
    max_length = 0
    length = 0
    for i: plaintext[int] in range(1, N):
        if (Seq[i] == Sym):
            length = (length + 1)
        else:
            length = 0
        if (length > max_length):
            max_length = length
    return max_length
