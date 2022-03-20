from UTIL import shared

# Array A contains linearization of a MxK matrix
# Array B contains linearization of a K*N matrix
# Array C of 0's is the result M*N matrix
# A = [0,2,1,0,3,4,2,3,10] 3x3 matrix
# B = [10,1,5,2,15,0,10,1000,1,1,2,3] 3x4 matrix
# C = [0,0,0,0,0,0,0,0,0,0,0,0] 3x4 matrix of 0's

# requires: len(A) == M*K, len(B) == K*N, len(C) = M*N, C is an array of 0's
def matrix_multiply(
    A: shared[list[int]], B: shared[list[int]], C: shared[list[int]], M: int, N: int, K: int) -> shared[list[int]]:
    for i in range(M):
        for j in range(N):
            for k in range(K):
                # C[i,j] = C[i,j] + A[i,k]*B[k,j]
                C[i*N+j] = C[i*N+j] + A[i*K+k]*B[k*N+j]
    return C


A = [0,2,1,0,3,4,2,3,10]
B = [10,1,5,2,15,0,10,1000,1,1,2,3]
C = [0,0,0,0,0,0,0,0,0,0,0,0]
M = 3
N = 4
K = 3
print(matrix_multiply(A, B, C, M, N, K))
