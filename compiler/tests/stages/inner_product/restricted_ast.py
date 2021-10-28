def foo(A, B, N):
    sum = 0
    for i in range(0, N):
        temp = (A[i] * B[i])
        sum = (sum + temp)
    return sum
