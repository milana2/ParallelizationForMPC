from UTIL import shared

# kmeans iteration: data and clusters are 2-dimensional points (x,y). First computes closest cluster per data point, then recomputes clusters.
# 
# requires: len(data_x) == len(data_y) == len, len(cluster_x) == len(cluster_y) == num_cluster
# OUTPUT_cluster_x and OUTPUT_cluster_y are arrays of 0's
# len(OUTPUT_cluster_x) == len(OUTPUT_cluster_y) == num_clusters 
# bestMap is an array of 0's
# len(bestMap) = len
def kmeans_iteration(data_x: shared[list[int]], data_y: shared[list[int]], cluster_x: shared[list[int]], cluster_y: shared[list[int]], OUTPUT_cluster_x: shared[list[int]], OUTPUT_cluster_y: shared[list[int]], len: int, num_cluster: int, bestMap: list[int]) -> (shared[list[int]], shared[list[int]]):
    
    # Compute nearest clusters for Data item i
    for i in range(len):
        best_dist = 10000 # dist2(cluster[0], cluster[1], dx, dy);
        for c in range(num_cluster):
            x_dist = cluster_x[c]-data_x[i] 
            x_sq = x_dist*x_dist
            y_dist = cluster_y[c]-data_y[i]
            y_sq = y_dist*y_dist
            dist = x_sq + y_sq
            val = bestMap[i]
            if dist < best_dist:
                best_dist = dist;
                val = c;
            bestMap[i] = val

    # Recompute cluster Pos
    for c in range(num_cluster):
        val_x = 0
        val_y = 0
        count = 0
        for i in range(len):
            if c == bestMap[i]:
               val_x = val_x + data_x[i]
               val_y = val_y + data_y[i]
               count = count+1
        if count > 0:
            val_x = val_x/count # Not sure if MOTION has intiger div?
            val_y = val_y/count 
        OUTPUT_cluster_x[c] = val_x
        OUTPUT_cluster_y[c] = val_y

    return (OUTPUT_cluster_x, OUTPUT_cluster_y)

# Data is two-dimensional, 200 datapoints, 100 from Party A and 100 from Party B
len = 200
data_x = [i for i in range(len)]
data_y = [len-i for i in range(len)]
num_cluster = 5
cluster_x = [i for i in range(5)]
cluster_y = [i+1 for i in range(5)]
OUTPUT_cluster_x = [0 for i in range(num_cluster)]
OUTPUT_cluster_y = [0 for i in range(num_cluster)]
bestMap = [0 for i in range(len)]
print(kmeans_iteration(data_x,data_y,cluster_x,cluster_y,OUTPUT_cluster_x,OUTPUT_cluster_y,len,num_cluster,bestMap))
 

