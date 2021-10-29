def foo(A, B, N, num_bins):
    result = []
    for i in range(0, num_bins):
        result = (result + [0])
    for i in range(0, num_bins):
        for j in range(0, N):
            if (A[j] == i):
                result[i] = (result[i] + B[j])
    return result
