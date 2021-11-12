def convex_hull(X_coords: list[int], Y_coords: list[int], N):
    hull_X: list[int] = []
    hull_Y: list[int] = []

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

        if is_hull:
            hull_X = hull_X + [p1_X]
            hull_Y = hull_Y + [p1_Y]

    return [hull_X, hull_Y]
