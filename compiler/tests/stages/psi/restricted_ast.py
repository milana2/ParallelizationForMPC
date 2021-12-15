def psi(A: shared, SA: plaintext, B: shared, SB: plaintext):
    dummy = 0
    result = []
    for i in range(0, SA):
        flag = False
        for j in range(0, SB):
            if (A[i] == B[j]):
                flag = True
        val = dummy
        if flag:
            val = A[i]
        result = (result + [val])
    return result
