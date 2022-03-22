from UTIL import shared

# input is a 2-d matrix of shared integer values and 
# OUTPUT_res is the result 2-d matrix of non-negative values
# It turns all negative values in input matrix into 0s

# requires: len(input)==len(OUTPUT_res)==len_outer*len_inner
# OUTPUT_res is array of 0's
def mnist_decomposed_relu(input: shared[list[int]], OUTPUT_res: shared[list[int]], len_outer: int, len_inner: int) -> shared[list[int]]:
    for i in range(len_outer): 
        for j in range(len_inner):
            val = 0
            if input[i*len_inner+j] > 0:
              val = input[i*len_inner+j]
            OUTPUT_res[i*len_inner+j] = val
    return OUTPUT_res

len_inner = 10
len_outer = 20
input = [i if i%2 == 0 else -2*i for i in range(len_inner*len_outer)]
OUTPUT_res = [0 for i in range(len_inner*len_outer)]
print(mnist_decomposed_relu(input, OUTPUT_res, len_outer, len_inner))

