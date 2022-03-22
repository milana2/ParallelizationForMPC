from UTIL import shared

# Array A is a the input array of integers i, merges the arrays of two parties
# Array V is a same-size result array, contains variance
# A = [0,2,1,0,3,4,2,3]
# V = [0,0,0,0,0,0,0,0]

A = [0,2,1,0,3,4,2,3]
V = [0,0,0,0,0,0,0,0]
len = 8
# requires: len(A) == len(V) == len
# V is an array of 0s
def variance(A: shared[list[int]], V: shared[list[int]], len: int) -> shared[int]:
    sum = 0
    for i in range(len):
        sum = sum + A[i]
    # Does MOTION have integer division operation
    exp = sum/len
    for i in range(len):
        dist = A[i] - exp
        V[i] = dist*dist
    res = 0
    for i in range(len):
        res = res + V[i]
    variance = res/len
    return variance

A = [0,2,1,0,3,4,2,3]
V = [0,0,0,0,0,0,0,0]
len = 8
print(variance(A,V,len))


