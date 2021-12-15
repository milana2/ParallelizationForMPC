def count_123(Seq: shared, N: plaintext, Syms: shared):
    s1 = False
    s2 = False
    s3 = False
    c = 0
    for i in range(0, N):
        if ((Seq[i] == Syms[3]) and (s2 or s1)):
            c = (c + 1)
        s2 = ((Seq[i] == Syms[2]) and (s1 or s2))
        s1 = (Seq[i] == Syms[1])
    return c
