def minimal_points(X_coords: shared, Y_coords: shared, N: plaintext):
    min_X = []
    min_Y = []
    for i: plaintext in range(0, N):
        bx = False
        for j: plaintext in range(0, N):
            bx = (bx or ((X_coords[j] < X_coords[i]) and (Y_coords[j] < Y_coords[i])))
        if not bx:
            min_X = (min_X + [X_coords[i]])
            min_Y = (min_Y + [Y_coords[i]])
    return (min_X, min_Y)
