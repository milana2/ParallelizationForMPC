def kmeans_iteration(data_x: shared[list[int; ?]], data_y: shared[list[int; ?]], cluster_x: shared[list[int; ?]], cluster_y: shared[list[int; ?]], OUTPUT_cluster_x: shared[list[int; ?]], OUTPUT_cluster_y: shared[list[int; ?]], len: plaintext[int], num_cluster: plaintext[int], bestMap: plaintext[list[int; ?]]) -> tuple[shared[list[int; ?]], shared[list[int; ?]]]:
    for i: plaintext[int] in range(0, len):
        best_dist = 10000
        for c: plaintext[int] in range(0, num_cluster):
            x_dist = (cluster_x[c] - data_x[i])
            x_sq = (x_dist * x_dist)
            y_dist = (cluster_y[c] - data_y[i])
            y_sq = (y_dist * y_dist)
            dist = (x_sq + y_sq)
            val = bestMap[i]
            if (dist < best_dist):
                best_dist = dist
                val = c
            bestMap[i] = val
    for c: plaintext[int] in range(0, num_cluster):
        val_x = 0
        val_y = 0
        count = 0
        for i: plaintext[int] in range(0, len):
            if (c == bestMap[i]):
                val_x = (val_x + data_x[i])
                val_y = (val_y + data_y[i])
                count = (count + 1)
        if (count > 0):
            val_x = (val_x / count)
            val_y = (val_y / count)
        OUTPUT_cluster_x[c] = val_x
        OUTPUT_cluster_y[c] = val_y
    return (OUTPUT_cluster_x, OUTPUT_cluster_y)
