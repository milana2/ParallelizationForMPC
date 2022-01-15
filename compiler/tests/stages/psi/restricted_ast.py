def psi(A: shared[list[int]], SA: plaintext[int], B: shared[list[int]], SB: plaintext[int]) -> shared[list[int]]:
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
