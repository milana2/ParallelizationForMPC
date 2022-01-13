import typing

# returns a list[int] which is the intersection
# of privite sets of integers A and B
# requires: no repetition of elements in either A or B
# requires: len(A) = SA, len(B) = SB
def psi(A: list[int], SA, B: list[int], SB) -> list[int]:
    dummy: int = 0
    result: list[int] = []
    for i in range(0, SA):
        flag: Bool = False
        for j in range(0, SB):
            if A[i] == B[j]:
                flag = True
        val: int = dummy
        if flag:
            val: int = A[i]
        # overloaded +. This is append actually.
        result = result + [val]
    return result


A = [4, 2, 3, 1, 10]
B = [2, 10, 3, 4, 5, 6, 7]
print(psi(A, 5, B, 7))
