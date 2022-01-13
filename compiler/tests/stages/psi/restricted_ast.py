def psi(A: shared[list[std::uint32_t]], SA: plaintext[std::uint32_t], B: shared[list[std::uint32_t]], SB: plaintext[std::uint32_t]):
    dummy = 0
    result = []
    for i: plaintext[int] in range(0, SA):
        flag = False
        for j: plaintext[int] in range(0, SB):
            if (A[i] == B[j]):
                flag = True
        val = dummy
        if flag:
            val = A[i]
        result = (result + [val])
    return result
