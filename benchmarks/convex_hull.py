from UTIL import shared


def convex_hull(
    X_coords: shared[list[int]], Y_coords: shared[list[int]], N: int
) -> tuple[shared[list[int]], shared[list[int]]]:
    hull_X: list[int] = []
    hull_Y: list[int] = []

    dummy: int = 0

    for i in range(0, N):
        is_hull = True
        p1_X = X_coords[i]
        p1_Y = Y_coords[i]

        if p1_X <= 0 and p1_Y >= 0:
            for j in range(0, N):
                p2_X = X_coords[j]
                p2_Y = Y_coords[j]

                if not (p1_X <= p2_X or p1_Y >= p2_Y):
                    is_hull = False
        val_X: int = dummy
        val_Y: int = dummy            
        
        if is_hull:
            val_X = p1_X
            val_Y = p1_Y
        hull_X = hull_X + [val_X]
        hull_Y = hull_Y + [val_Y]

    return (hull_X, hull_Y)

X_coords = [1, 2, 3]
Y_coords = [4, 5, 6]
print(convex_hull(X_coords, Y_coords, 3))
