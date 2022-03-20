from UTIL import shared

# Floyd-Warshall's algorithm for computing shortest distance between vertices 
# Array Dist is the N*N distance matrix
# Dist = [0,10000,-2,10000,4,0,3,10000,10000,10000,0,2,10000,-1,10000,0]
# N is number of vertices

# requires: len(Dist) == N*N
# Dist[i,i] = 0, Dist[i,j] = weights(i,j) if edge i->j, Dist[i,j] = infinity otherwise 
def floyd_warshall(
    Dist: shared[list[int]], N: int) -> shared[list[int]]:
    for k in range(N):
        for i in range(N):
            for j in range(N):
                if Dist[i*N+j] > Dist[i*N+k]+Dist[k*N+j]:
                    Dist[i*N+j] = Dist[i*N+k]+Dist[k*N+j]
    return Dist

# Wishful. Array write extension may require modification to handle!!!
# 10000 = infinity
Dist = [0,10000,-2,10000,4,0,3,10000,10000,10000,0,2,10000,-1,10000,0]
N = 4
print(floyd_warshall(Dist, N))
