def ip(A: shared, B: shared, N: plaintext):
    sum = 0
    for i: plaintext in range(0, N):
        temp = (A[i] * B[i])
        sum = (sum + temp)
    return sum
