def histogram(A: shared[list[int; ?]], B: shared[list[int; ?]], N: plaintext[int], num_bins: plaintext[int], result: plaintext[list[int; ?]]) -> shared[list[int; ?]]:
    for i: plaintext[int] in range(0, num_bins):
        for j: plaintext[int] in range(0, N):
            if (A[j] == i):
                val = (result[i] + B[j])
            else:
                val = result[i]
            result[i] = val
    return result
