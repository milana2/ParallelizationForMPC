import typing


def ip(A: list[int], B: list[int], N):
    sum = 0
    for i in range(0, N):
        temp = A[i] * B[i]
        sum = sum + temp
    return sum


A = [1, 2, 3]
B = [4, 5, 6]
print(ip(A, B, 3))
