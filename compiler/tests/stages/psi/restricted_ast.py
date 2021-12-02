def foo(A, SA, B, SB):
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
