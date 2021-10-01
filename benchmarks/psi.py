import typing

# returns a list[int] which is the intersection 
# of privite sets of integers A and B
# requires: no repetition of elements in either A or B
# requires: len(A) = SA, len(B) = SB
def psi(A: list[int], SA, B: list[int], SB) -> list[int]:
  result: list[int] = []
  for i in range(0,SA):
    for j in range(0,SB):
      if A[i] == B[j]:
        #overloaded +. This is append actually.
        result = result + [A[i]]
  return result

A = [1,2,3]
B = [2]
intersect = psi(A,3,B,1)
print(intersect)

