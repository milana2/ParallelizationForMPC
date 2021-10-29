def foo(A, SA, B, SB):
    result = []
    for i in range(0, SA):
        for j in range(0, SB):
            if (A[i] == B[j]):
                result = (result + [A[i]])
    return result
