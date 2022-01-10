def ip(A: shared[list[unsigned int]], B: shared[list[unsigned int]], N: plaintext[unsigned int]):
    sum = 0
    for i: plaintext[int] in range(0, N):
        temp = (A[i] * B[i])
        sum = (sum + temp)
    return sum
