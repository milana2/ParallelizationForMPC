def foo(x: shared[unsigned int], y: shared[unsigned int]):
    z = 0
    if (x > 0):
        if (y > 0):
            z = 1
        else:
            z = - 1
    return z
