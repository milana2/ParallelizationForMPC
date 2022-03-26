from UTIL import shared

# requires: result_Y and result_X are arrays of dummy values (0's)
def minimal_points(
    X_coords: shared[list[int]], Y_coords: shared[list[int]], N: int, result_X: shared[list[int]], result_Y: shared[list[int]]
) -> tuple[shared[list[int]], shared[list[int]]]:
    min_X: list[int] = []
    min_Y: list[int] = []

    # dummy: int = 0
    for i in range(0, N):
        bx = False
        for j in range(0, N):
            bx = bx or (X_coords[j] < X_coords[i] and Y_coords[j] < Y_coords[i])
        val_X: int = result_X[i]
        val_Y: int = result_Y[i]    
        if not bx:
            val_X = X_coords[i]
            val_Y = Y_coords[i]
        result_X[i] = val_X
        result_Y[i] = val_Y
        
    return (result_X, result_Y)


X_coords = [1, 2, 3]
Y_coords = [4, 5, 6]
result_X = [0 for i in range(len(X_coords))]
result_Y = [0 for i in range(len(Y_coords))]
print(minimal_points(X_coords, Y_coords, 3, result_X, result_Y))
