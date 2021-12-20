def histogram(A: shared, B: shared, N: plaintext, num_bins: plaintext):
    result = []
    for i: plaintext in range(0, num_bins):
        result = (result + [0])
    for i: plaintext in range(0, num_bins):
        for j: plaintext in range(0, N):
            if (A[j] == i):
                result[i] = (result[i] + B[j])
    return result
