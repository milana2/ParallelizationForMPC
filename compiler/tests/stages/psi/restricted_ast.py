def psi(A: shared, SA: plaintext, B: shared, SB: plaintext):
    dummy = 0
    result = []
    for i: plaintext in range(0, SA):
        flag = False
        for j: plaintext in range(0, SB):
            if (A[i] == B[j]):
                flag = True
        val = dummy
        if flag:
            val = A[i]
        result = (result + [val])
    return result
