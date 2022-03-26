from UTIL import shared


def minimal_points(
    X_coords: shared[list[int]], Y_coords: shared[list[int]], N: int
) -> tuple[shared[list[int]], shared[list[int]]]:
    min_X: list[int] = []
    min_Y: list[int] = []

    dummy: int = 0
    for i in range(0, N):
        bx = False
        for j in range(0, N):
            bx = bx or (X_coords[j] < X_coords[i] and Y_coords[j] < Y_coords[i])
        val_X: int = dummy
        val_Y: int = dummy    
        if not bx:
            val_X = X_coords[i]
            val_Y = Y_coords[i]
        min_X = min_X + [val_X]
        min_Y = min_Y + [val_Y]
        
    return (min_X, min_Y)


X_coords = [1, 2, 3]
Y_coords = [4, 5, 6]
print(minimal_points(X_coords, Y_coords, 3))
