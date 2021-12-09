def foo(Seq, N, Sym):
    max_length = 0
    length = 0
    for i in range(1, N):
        if (Seq[i] == Sym):
            length = (length + 1)
        else:
            length = 0
        if (length > max_length):
            max_length = length
    return max_length
