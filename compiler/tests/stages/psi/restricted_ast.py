def psi(A: shared[list[unsigned int]], SA: plaintext[unsigned int], B: shared[list[unsigned int]], SB: plaintext[unsigned int]):
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
