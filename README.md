# Compiler stages with different benchmarks
## `biometric`
### Input
```python
import typing

# Biometric matching
# D is the number of features we are matching. Usually small, e.g., D=4
# N is the size of the database S
# C is the vector of features we are tryign to match.
# S is the (originally two dimentional) database array: S[0,0],S[0,1],..S[0,D-1],S[1,0]... S[N-1,D-1]
def biometric(C: list[int], D, S: list[int], N):
  min_sum: int = 10000
  min_index = -1
  for i in range(N):
    sum = 0
    for j in range(D):
      d = S[i*D+j]-C[j] 
      p = d*d      
      sum = sum + p
    if sum < min_sum:
      min_sum = sum
      min_index = i

  return (min_sum,min_index)

C = [1,2,3,4]
S = [4,5,2,10,2,120,4,10,99,88,77,66,55,44,33,22]
print(biometric(C,4,S,4))

```
### Restricted AST
```python
def biometric(C: shared[list[int]], D: plaintext[int], S: shared[list[int]], N: plaintext[int]):
    min_sum = 10000
    min_index = - 1
    for i: plaintext[int] in range(0, N):
        sum = 0
        for j: plaintext[int] in range(0, D):
            d = (S[((i * D) + j)] - C[j])
            p = (d * d)
            sum = (sum + p)
        if (sum < min_sum):
            min_sum = sum
            min_index = i
    return (min_sum, min_index)
```
### Three-address code CFG
![](biometric_tac_cfg.png)
### SSA
![](biometric_ssa.png)
### SSA ϕ→MUX
![](biometric_ssa_mux.png)
### Dead code elimination
![](biometric_dead_code_elim.png)
### Linear code with loops
```python
def biometric(C: shared[list[int]], D: plaintext[int], S: shared[list[int]], N: plaintext[int]):
    min_sum!1 = 10000
    min_index!1 = - 1
    for i in range(0, N!0):
        min_sum!2 = Φ(min_sum!1, min_sum!4)
        min_index!2 = Φ(min_index!1, min_index!4)
        sum!2 = 0
        for j in range(0, D!0):
            sum!3 = Φ(sum!2, sum!4)
            d!3 = (S!0[((i * D!0) + j)] - C!0[j])
            p!3 = (d!3 * d!3)
            sum!4 = (sum!3 + p!3)
        !1!2 = (sum!3 < min_sum!2)
        min_sum!3 = sum!3
        min_index!3 = i
        min_sum!4 = MUX(!1!2, min_sum!3, min_sum!2)
        min_index!4 = MUX(!1!2, min_index!3, min_index!2)
    !2!1 = (min_sum!2, min_index!2)
    return !2!1
```
### Dependency graph
![](biometric_dep_graph.png)
### Removal of infeasible edges
![](biometric_remove_infeasible_edges.png)
### Array MUX refinement
```python
def biometric(C: shared[list[int]], D: plaintext[int], S: shared[list[int]], N: plaintext[int]):
    min_sum!1 = 10000
    min_index!1 = - 1
    for i in range(0, N!0):
        min_sum!2 = Φ(min_sum!1, min_sum!4)
        min_index!2 = Φ(min_index!1, min_index!4)
        sum!2 = 0
        for j in range(0, D!0):
            sum!3 = Φ(sum!2, sum!4)
            d!3 = (S!0[((i * D!0) + j)] - C!0[j])
            p!3 = (d!3 * d!3)
            sum!4 = (sum!3 + p!3)
        !1!2 = (sum!3 < min_sum!2)
        min_sum!3 = sum!3
        min_index!3 = i
        min_sum!4 = MUX(!1!2, min_sum!3, min_sum!2)
        min_index!4 = MUX(!1!2, min_index!3, min_index!2)
    !2!1 = (min_sum!2, min_index!2)
    return !2!1
```
### Array MUX refinement (dependence graph)
![](biometric_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `C!0` | `shared[list[int]]` |
| `D!0` | `plaintext[int]` |
| `S!0` | `shared[list[int]]` |
| `N!0` | `plaintext[int]` |
| `i` | `plaintext[int]` |
| `j` | `plaintext[int]` |
| `min_index!3` | `plaintext[int]` |
| `min_index!4` | `shared[int]` |
| `d!3` | `shared[int]` |
| `p!3` | `shared[int]` |
| `sum!4` | `shared[int]` |
| `sum!2` | `plaintext[int]` |
| `min_index!1` | `plaintext[int]` |
| `min_sum!1` | `plaintext[int]` |
## `biometric_fast`
### Input
```python
import typing

def biometric_matching_fast(D, N, C:list[int], C_sqr_sum:int, two_C:list[int], S: list[int], S_sqr_sum: list[int]):
  """
  Computes biometric matching

  This version uses some preprocessed data from parties to provide faster biometric matching

  :param int D: the cardinality of a feature vector, Usually small, e.g. 4
  :param int N: number of features in the database e.g. usually 1024, 2048, 4096, etc
  :param list[int] C: query feature vector, we need to find closest match to this vector in the DB, comes from client (Alice)
  :param int C_sqr_sum: sum of squares of elements of `C` e.g. if `C={1, 2, 3, 4}`, then `C_sqr_sum is: 1*1 + 2*2 + 3*3 + 4*4 = 30`
   client passes it pre-processed to to save gates in circuit
  :param list[int] two_C: same as `C` except that each element is multipled by 2, e.g. if `C={1, 2, 3, 4}`, then
   `two_C = {2, 4, 6, 8}`. client passes it preprocessed to save gates
  :param list[int] S: the database of features, it has N * D elements i.e. N features and each feature vector has D elements,
   this comes from server (Bob)
  :param list[int] S_sqr_sum: has N elements, each element is sum of squares of corresponding feature elements e.g. say
   S={{1, 2, 3, 4}, {5, 6, 7, 8}}, then S_sqr_sum={1*1 + 2*2 + 3*3 + 4*4, 5*5 + 6*6 + 7*7 + 8*8} = {30, 174}

  """

  differences: list[int] = []
  for i in range(D):
    differences[i] = differences + [0]

  for i in range(N):
    a_sqr_plus_b_sqr: int = S_sqr_sum[i] + C_sqr_sum
    two_a_b: int = 0

    for j in range(D):
      tmp: int = S[i*D+j] * two_C[j]
      two_a_b = two_a_b + tmp

    this_diff: int = a_sqr_plus_b_sqr - two_a_b
    differences[i] = this_diff


    min_diff: int = differences[0]
    min_index: int = 0

    for k in range(N):
      if(differences[k] < min_diff):
        min_diff = differences[k]
        min_index = k

  return (min_diff, min_index)



def test_biometric_matching_fast(D, N, C, S):
  """
  just a convenience method for testing, computes the pre-processing data for the actual call
  """
  two_C = [0] * D
  C_sqr_sum = 0
  S_sqr_sum = [0] * N
  for i in range(D):
    two_C[i] = 2 * C[i]
    C_sqr_sum = C_sqr_sum + (C[i] * C[i])

  for i in range(N):
    for j in range(D):
      S_sqr_sum[i] = S_sqr_sum[i] + (S[i*D+j] * S[i*D+j])

  print(biometric_matching__fast(D, N, C, C_sqr_sum, two_C, S, S_sqr_sum))


C = [1,2,3,4]
S = [4,5,2,10,2,120,4,10,99,88,77,66,55,44,33,22]
test_biometric_matching_fast(4, 4, C, S)

```
### Restricted AST
```python
def biometric_matching_fast(D: plaintext[int], N: plaintext[int], C: shared[list[int]], C_sqr_sum: shared[int], two_C: shared[list[int]], S: shared[list[int]], S_sqr_sum: shared[list[int]]):
    differences = []
    for i: plaintext[int] in range(0, D):
        differences[i] = (differences + [0])
    for i: plaintext[int] in range(0, N):
        a_sqr_plus_b_sqr = (S_sqr_sum[i] + C_sqr_sum)
        two_a_b = 0
        for j: plaintext[int] in range(0, D):
            tmp = (S[((i * D) + j)] * two_C[j])
            two_a_b = (two_a_b + tmp)
        this_diff = (a_sqr_plus_b_sqr - two_a_b)
        differences[i] = this_diff
        min_diff = differences[0]
        min_index = 0
        for k: plaintext[int] in range(0, N):
            if (differences[k] < min_diff):
                min_diff = differences[k]
                min_index = k
    return (min_diff, min_index)
```
### Three-address code CFG
![](biometric_fast_tac_cfg.png)
### SSA
![](biometric_fast_ssa.png)
### SSA ϕ→MUX
![](biometric_fast_ssa_mux.png)
### Dead code elimination
![](biometric_fast_dead_code_elim.png)
### Linear code with loops
```python
def biometric_matching_fast(D: plaintext[int], N: plaintext[int], C: shared[list[int]], C_sqr_sum: shared[int], two_C: shared[list[int]], S: shared[list[int]], S_sqr_sum: shared[list[int]]):
    differences!1 = []
    for i in range(0, D!0):
        differences!2 = Φ(differences!1, differences!3)
        !1!2 = [0]
        !2!2 = (differences!2 + !1!2)
        differences!3 = Update(differences!2, i, !2!2)
    for i in range(0, N!0):
        differences!4 = Φ(differences!2, differences!5)
        min_diff!1 = Φ(min_diff!0, min_diff!3)
        min_index!1 = Φ(min_index!0, min_index!3)
        a_sqr_plus_b_sqr!2 = (S_sqr_sum!0[i] + C_sqr_sum!0)
        two_a_b!2 = 0
        for j in range(0, D!0):
            two_a_b!3 = Φ(two_a_b!2, two_a_b!4)
            tmp!3 = (S!0[((i * D!0) + j)] * two_C!0[j])
            two_a_b!4 = (two_a_b!3 + tmp!3)
        this_diff!2 = (a_sqr_plus_b_sqr!2 - two_a_b!3)
        differences!5 = Update(differences!4, i, this_diff!2)
        min_diff!2 = differences!5[0]
        min_index!2 = 0
        for k in range(0, N!0):
            min_diff!3 = Φ(min_diff!2, min_diff!5)
            min_index!3 = Φ(min_index!2, min_index!5)
            !3!3 = (differences!5[k] < min_diff!3)
            min_diff!4 = differences!5[k]
            min_index!4 = k
            min_diff!5 = MUX(!3!3, min_diff!4, min_diff!3)
            min_index!5 = MUX(!3!3, min_index!4, min_index!3)
    !4!1 = (min_diff!1, min_index!1)
    return !4!1
```
### Dependency graph
![](biometric_fast_dep_graph.png)
### Removal of infeasible edges
![](biometric_fast_remove_infeasible_edges.png)
### Array MUX refinement
```python
def biometric_matching_fast(D: plaintext[int], N: plaintext[int], C: shared[list[int]], C_sqr_sum: shared[int], two_C: shared[list[int]], S: shared[list[int]], S_sqr_sum: shared[list[int]]):
    differences!1 = []
    for i in range(0, D!0):
        differences!2 = Φ(differences!1, differences!3)
        !1!2 = [0]
        !2!2 = (differences!2 + !1!2)
        differences!3 = Update(differences!2, i, !2!2)
    for i in range(0, N!0):
        differences!4 = Φ(differences!2, differences!5)
        min_diff!1 = Φ(min_diff!0, min_diff!3)
        min_index!1 = Φ(min_index!0, min_index!3)
        a_sqr_plus_b_sqr!2 = (S_sqr_sum!0[i] + C_sqr_sum!0)
        two_a_b!2 = 0
        for j in range(0, D!0):
            two_a_b!3 = Φ(two_a_b!2, two_a_b!4)
            tmp!3 = (S!0[((i * D!0) + j)] * two_C!0[j])
            two_a_b!4 = (two_a_b!3 + tmp!3)
        this_diff!2 = (a_sqr_plus_b_sqr!2 - two_a_b!3)
        differences!5 = Update(differences!4, i, this_diff!2)
        min_diff!2 = differences!5[0]
        min_index!2 = 0
        for k in range(0, N!0):
            min_diff!3 = Φ(min_diff!2, min_diff!5)
            min_index!3 = Φ(min_index!2, min_index!5)
            !3!3 = (differences!5[k] < min_diff!3)
            min_diff!4 = differences!5[k]
            min_index!4 = k
            min_diff!5 = MUX(!3!3, min_diff!4, min_diff!3)
            min_index!5 = MUX(!3!3, min_index!4, min_index!3)
    !4!1 = (min_diff!1, min_index!1)
    return !4!1
```
### Array MUX refinement (dependence graph)
![](biometric_fast_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `D!0` | `plaintext[int]` |
| `N!0` | `plaintext[int]` |
| `C!0` | `shared[list[int]]` |
| `C_sqr_sum!0` | `shared[int]` |
| `two_C!0` | `shared[list[int]]` |
| `S!0` | `shared[list[int]]` |
| `S_sqr_sum!0` | `shared[list[int]]` |
| `i` | `plaintext[int]` |
| `j` | `plaintext[int]` |
| `k` | `plaintext[int]` |
| `min_index!4` | `plaintext[int]` |
| `min_index!5` | `shared[int]` |
| `min_index!2` | `plaintext[int]` |
| `tmp!3` | `shared[int]` |
| `two_a_b!4` | `shared[int]` |
| `two_a_b!2` | `plaintext[int]` |
| `a_sqr_plus_b_sqr!2` | `shared[int]` |
| `this_diff!2` | `shared[int]` |
| `differences!5` | `shared[list[int]]` |
| `min_diff!4` | `shared[int]` |
| `min_diff!5` | `shared[int]` |
| `!3!3` | `shared[int]` |
| `min_diff!2` | `shared[int]` |
| `!1!2` | `plaintext[list[int]]` |
| `differences!1` | `plaintext[list[int]]` |
## `chapterfour_figure_12`
### Input
```python
def foo(x, y):
    z = 0
    if x > 0:
        if y > 0:
            z = 1
        else:
            z = -1
    return z

```
### Restricted AST
```python
def foo(x: plaintext[int], y: plaintext[int]):
    z = 0
    if (x > 0):
        if (y > 0):
            z = 1
        else:
            z = - 1
    return z
```
### Three-address code CFG
![](chapterfour_figure_12_tac_cfg.png)
### SSA
![](chapterfour_figure_12_ssa.png)
### SSA ϕ→MUX
![](chapterfour_figure_12_ssa_mux.png)
### Dead code elimination
![](chapterfour_figure_12_dead_code_elim.png)
### Linear code with loops
```python
def foo(x: plaintext[int], y: plaintext[int]):
    z!1 = 0
    !1!1 = (x!0 > 0)
    !2!1 = (y!0 > 0)
    z!3 = - 1
    z!2 = 1
    z!4 = MUX(!2!1, z!2, z!3)
    z!5 = MUX(!1!1, z!1, z!4)
    return z!5
```
### Dependency graph
![](chapterfour_figure_12_dep_graph.png)
### Removal of infeasible edges
![](chapterfour_figure_12_remove_infeasible_edges.png)
### Array MUX refinement
```python
def foo(x: plaintext[int], y: plaintext[int]):
    z!1 = 0
    !1!1 = (x!0 > 0)
    !2!1 = (y!0 > 0)
    z!3 = - 1
    z!2 = 1
    z!4 = MUX(!2!1, z!2, z!3)
    z!5 = MUX(!1!1, z!1, z!4)
    return z!5
```
### Array MUX refinement (dependence graph)
![](chapterfour_figure_12_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `x!0` | `plaintext[int]` |
| `y!0` | `plaintext[int]` |
| `z!2` | `plaintext[int]` |
| `z!4` | `shared[int]` |
| `z!5` | `shared[int]` |
| `z!3` | `plaintext[int]` |
| `!2!1` | `plaintext[int]` |
| `!1!1` | `plaintext[int]` |
| `z!1` | `plaintext[int]` |
## `convex_hull`
### Input
```python
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

    return (hull_X, hull_Y)

```
### Restricted AST
```python
def convex_hull(X_coords: shared[list[int]], Y_coords: shared[list[int]], N: plaintext[int]):
    hull_X = []
    hull_Y = []
    for i: plaintext[int] in range(0, N):
        is_hull = True
        p1_X = X_coords[i]
        p1_Y = Y_coords[i]
        if ((p1_X <= 0) and (p1_Y >= 0)):
            for j: plaintext[int] in range(0, N):
                p2_X = X_coords[j]
                p2_Y = Y_coords[j]
                if not ((p1_X <= p2_X) or (p1_Y >= p2_Y)):
                    is_hull = False
        if is_hull:
            hull_X = (hull_X + [p1_X])
            hull_Y = (hull_Y + [p1_Y])
    return (hull_X, hull_Y)
```
### Three-address code CFG
![](convex_hull_tac_cfg.png)
### SSA
![](convex_hull_ssa.png)
### SSA ϕ→MUX
![](convex_hull_ssa_mux.png)
### Dead code elimination
![](convex_hull_dead_code_elim.png)
### Linear code with loops
```python
def convex_hull(X_coords: shared[list[int]], Y_coords: shared[list[int]], N: plaintext[int]):
    hull_X!1 = []
    hull_Y!1 = []
    for i in range(0, N!0):
        hull_X!2 = Φ(hull_X!1, hull_X!4)
        hull_Y!2 = Φ(hull_Y!1, hull_Y!4)
        is_hull!2 = True
        p1_X!2 = X_coords!0[i]
        p1_Y!2 = Y_coords!0[i]
        !1!2 = (p1_X!2 <= 0)
        !2!2 = (p1_Y!2 >= 0)
        !3!2 = (!1!2 and !2!2)
        for j in range(0, N!0):
            is_hull!3 = Φ(is_hull!2, is_hull!5)
            p2_X!3 = X_coords!0[j]
            p2_Y!3 = Y_coords!0[j]
            !6!3 = (p1_X!2 <= p2_X!3)
            !7!3 = (p1_Y!2 >= p2_Y!3)
            !8!3 = (!6!3 or !7!3)
            !9!3 = not !8!3
            is_hull!4 = False
            is_hull!5 = MUX(!9!3, is_hull!4, is_hull!3)
        is_hull!6 = MUX(!3!2, is_hull!2, is_hull!3)
        !10!2 = [p1_X!2]
        hull_X!3 = (hull_X!2 + !10!2)
        !11!2 = [p1_Y!2]
        hull_Y!3 = (hull_Y!2 + !11!2)
        hull_X!4 = MUX(is_hull!6, hull_X!3, hull_X!2)
        hull_Y!4 = MUX(is_hull!6, hull_Y!3, hull_Y!2)
    !12!1 = (hull_X!2, hull_Y!2)
    return !12!1
```
### Dependency graph
![](convex_hull_dep_graph.png)
### Removal of infeasible edges
![](convex_hull_remove_infeasible_edges.png)
### Array MUX refinement
```python
def convex_hull(X_coords: shared[list[int]], Y_coords: shared[list[int]], N: plaintext[int]):
    hull_X!1 = []
    hull_Y!1 = []
    for i in range(0, N!0):
        hull_X!2 = Φ(hull_X!1, hull_X!4)
        hull_Y!2 = Φ(hull_Y!1, hull_Y!4)
        is_hull!2 = True
        p1_X!2 = X_coords!0[i]
        p1_Y!2 = Y_coords!0[i]
        !1!2 = (p1_X!2 <= 0)
        !2!2 = (p1_Y!2 >= 0)
        !3!2 = (!1!2 and !2!2)
        for j in range(0, N!0):
            is_hull!3 = Φ(is_hull!2, is_hull!5)
            p2_X!3 = X_coords!0[j]
            p2_Y!3 = Y_coords!0[j]
            !6!3 = (p1_X!2 <= p2_X!3)
            !7!3 = (p1_Y!2 >= p2_Y!3)
            !8!3 = (!6!3 or !7!3)
            !9!3 = not !8!3
            is_hull!4 = False
            is_hull!5 = MUX(!9!3, is_hull!4, is_hull!3)
        is_hull!6 = MUX(!3!2, is_hull!2, is_hull!3)
        !10!2 = [p1_X!2]
        hull_X!3 = (hull_X!2 + !10!2)
        !11!2 = [p1_Y!2]
        hull_Y!3 = (hull_Y!2 + !11!2)
        hull_X!4 = MUX(is_hull!6, hull_X!3, hull_X!2)
        hull_Y!4 = MUX(is_hull!6, hull_Y!3, hull_Y!2)
    !12!1 = (hull_X!2, hull_Y!2)
    return !12!1
```
### Array MUX refinement (dependence graph)
![](convex_hull_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `X_coords!0` | `shared[list[int]]` |
| `Y_coords!0` | `shared[list[int]]` |
| `N!0` | `plaintext[int]` |
| `i` | `plaintext[int]` |
| `j` | `plaintext[int]` |
| `is_hull!4` | `plaintext[int]` |
| `is_hull!5` | `shared[int]` |
| `p2_Y!3` | `shared[int]` |
| `!7!3` | `shared[int]` |
| `!8!3` | `shared[int]` |
| `!9!3` | `shared[int]` |
| `p2_X!3` | `shared[int]` |
| `!6!3` | `shared[int]` |
| `p1_Y!2` | `shared[int]` |
| `!11!2` | `shared[list[int]]` |
| `hull_Y!3` | `shared[list[int]]` |
| `hull_Y!4` | `shared[list[int]]` |
| `!2!2` | `shared[int]` |
| `!3!2` | `shared[int]` |
| `p1_X!2` | `shared[int]` |
| `!10!2` | `shared[list[int]]` |
| `hull_X!3` | `shared[list[int]]` |
| `hull_X!4` | `shared[list[int]]` |
| `!1!2` | `shared[int]` |
| `is_hull!2` | `plaintext[int]` |
| `is_hull!6` | `shared[int]` |
| `hull_Y!1` | `plaintext[list[int]]` |
| `hull_X!1` | `plaintext[list[int]]` |
## `count_102`
### Input
```python
def count_102(Seq: list[int], N, Syms: list[int]):
    """
    Computes the number of instances of regex a(b*)c in a provided sequence.
    Syms is a list of form [a, b, c].
    """
    s0 = False
    c = 0

    for i in range(0, N):
        if s0 and (Seq[i] == Syms[2]):
            c = c + 1

        s0 = (Seq[i] == Syms[1]) or (s0 and (Seq[i] == Syms[0]))

    return c


seq = [1, 0, 2, 1, 0, 0, 2, 1, 2, 2]
num_102s = count_102(seq, len(seq), [1, 0, 2])
print(num_102s)

```
### Restricted AST
```python
def count_102(Seq: shared[list[int]], N: plaintext[int], Syms: shared[list[int]]):
    s0 = False
    c = 0
    for i: plaintext[int] in range(0, N):
        if (s0 and (Seq[i] == Syms[2])):
            c = (c + 1)
        s0 = ((Seq[i] == Syms[1]) or (s0 and (Seq[i] == Syms[0])))
    return c
```
### Three-address code CFG
![](count_102_tac_cfg.png)
### SSA
![](count_102_ssa.png)
### SSA ϕ→MUX
![](count_102_ssa_mux.png)
### Dead code elimination
![](count_102_dead_code_elim.png)
### Linear code with loops
```python
def count_102(Seq: shared[list[int]], N: plaintext[int], Syms: shared[list[int]]):
    s0!1 = False
    c!1 = 0
    for i in range(0, N!0):
        s0!2 = Φ(s0!1, s0!3)
        c!2 = Φ(c!1, c!4)
        !1!2 = (Seq!0[i] == Syms!0[2])
        !2!2 = (s0!2 and !1!2)
        c!3 = (c!2 + 1)
        c!4 = MUX(!2!2, c!3, c!2)
        !3!2 = (Seq!0[i] == Syms!0[1])
        !5!2 = (Seq!0[i] == Syms!0[0])
        !6!2 = (s0!2 and !5!2)
        s0!3 = (!3!2 or !6!2)
    return c!2
```
### Dependency graph
![](count_102_dep_graph.png)
### Removal of infeasible edges
![](count_102_remove_infeasible_edges.png)
### Array MUX refinement
```python
def count_102(Seq: shared[list[int]], N: plaintext[int], Syms: shared[list[int]]):
    s0!1 = False
    c!1 = 0
    for i in range(0, N!0):
        s0!2 = Φ(s0!1, s0!3)
        c!2 = Φ(c!1, c!4)
        !1!2 = (Seq!0[i] == Syms!0[2])
        !2!2 = (s0!2 and !1!2)
        c!3 = (c!2 + 1)
        c!4 = MUX(!2!2, c!3, c!2)
        !3!2 = (Seq!0[i] == Syms!0[1])
        !5!2 = (Seq!0[i] == Syms!0[0])
        !6!2 = (s0!2 and !5!2)
        s0!3 = (!3!2 or !6!2)
    return c!2
```
### Array MUX refinement (dependence graph)
![](count_102_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `Seq!0` | `shared[list[int]]` |
| `N!0` | `plaintext[int]` |
| `Syms!0` | `shared[list[int]]` |
| `i` | `plaintext[int]` |
| `!5!2` | `shared[int]` |
| `!6!2` | `shared[int]` |
| `s0!3` | `shared[int]` |
| `!3!2` | `shared[int]` |
| `!1!2` | `shared[int]` |
| `!2!2` | `shared[int]` |
| `c!1` | `plaintext[int]` |
| `s0!1` | `plaintext[int]` |
## `count_10s`
### Input
```python
def count_10s(Seq: list[int], N, Syms: list[int]):
    """
    Computes the number of instances of regex a(b+) in a provided sequence.
    Syms is a list of form [a, b].
    """
    s0 = False
    s1 = False
    scount = 0

    for i in range(0, N):
        if s1 and (Seq[i] != Syms[0]):
            scount = scount + 1

        s1 = (Seq[i] == Syms[0]) and (s0 or s1)
        s0 = Seq[i] == Syms[1]

    return scount


seq = [1, 0, 0, 1, 1, 0, 2]
num_10s = count_10s(seq, len(seq), [0, 1])
print(num_10s)

```
### Restricted AST
```python
def count_10s(Seq: shared[list[int]], N: plaintext[int], Syms: shared[list[int]]):
    s0 = False
    s1 = False
    scount = 0
    for i: plaintext[int] in range(0, N):
        if (s1 and (Seq[i] != Syms[0])):
            scount = (scount + 1)
        s1 = ((Seq[i] == Syms[0]) and (s0 or s1))
        s0 = (Seq[i] == Syms[1])
    return scount
```
### Three-address code CFG
![](count_10s_tac_cfg.png)
### SSA
![](count_10s_ssa.png)
### SSA ϕ→MUX
![](count_10s_ssa_mux.png)
### Dead code elimination
![](count_10s_dead_code_elim.png)
### Linear code with loops
```python
def count_10s(Seq: shared[list[int]], N: plaintext[int], Syms: shared[list[int]]):
    s0!1 = False
    s1!1 = False
    scount!1 = 0
    for i in range(0, N!0):
        s0!2 = Φ(s0!1, s0!3)
        s1!2 = Φ(s1!1, s1!3)
        scount!2 = Φ(scount!1, scount!4)
        !1!2 = (Seq!0[i] != Syms!0[0])
        !2!2 = (s1!2 and !1!2)
        scount!3 = (scount!2 + 1)
        scount!4 = MUX(!2!2, scount!3, scount!2)
        !3!2 = (Seq!0[i] == Syms!0[0])
        !4!2 = (s0!2 or s1!2)
        s1!3 = (!3!2 and !4!2)
        s0!3 = (Seq!0[i] == Syms!0[1])
    return scount!2
```
### Dependency graph
![](count_10s_dep_graph.png)
### Removal of infeasible edges
![](count_10s_remove_infeasible_edges.png)
### Array MUX refinement
```python
def count_10s(Seq: shared[list[int]], N: plaintext[int], Syms: shared[list[int]]):
    s0!1 = False
    s1!1 = False
    scount!1 = 0
    for i in range(0, N!0):
        s0!2 = Φ(s0!1, s0!3)
        s1!2 = Φ(s1!1, s1!3)
        scount!2 = Φ(scount!1, scount!4)
        !1!2 = (Seq!0[i] != Syms!0[0])
        !2!2 = (s1!2 and !1!2)
        scount!3 = (scount!2 + 1)
        scount!4 = MUX(!2!2, scount!3, scount!2)
        !3!2 = (Seq!0[i] == Syms!0[0])
        !4!2 = (s0!2 or s1!2)
        s1!3 = (!3!2 and !4!2)
        s0!3 = (Seq!0[i] == Syms!0[1])
    return scount!2
```
### Array MUX refinement (dependence graph)
![](count_10s_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `Seq!0` | `shared[list[int]]` |
| `N!0` | `plaintext[int]` |
| `Syms!0` | `shared[list[int]]` |
| `i` | `plaintext[int]` |
| `s0!3` | `shared[int]` |
| `!3!2` | `shared[int]` |
| `s1!3` | `shared[int]` |
| `!1!2` | `shared[int]` |
| `!2!2` | `shared[int]` |
| `scount!1` | `plaintext[int]` |
| `s1!1` | `plaintext[int]` |
| `s0!1` | `plaintext[int]` |
## `count_123`
### Input
```python
def count_123(Seq: list[int], N, Syms: list[int]):
    """
    Computes the number of instances of regex a*b*c* in a provided sequence.
    Syms is a list of form [a, b, c].
    """

    s1 = False
    s2 = False
    s3 = False
    c = 0

    for i in range(0, N):
        if Seq[i] == Syms[3] and (s2 or s1):
            c = c + 1
        s2 = (Seq[i] == Syms[2]) and (s1 or s2)
        s1 = Seq[i] == Syms[1]

    return c


seq = [1, 2, 3, 1, 3, 3, 4]
num_123s = count_123(seq, len(seq), [1, 2, 3])
print(num_123s)

```
### Restricted AST
```python
def count_123(Seq: shared[list[int]], N: plaintext[int], Syms: shared[list[int]]):
    s1 = False
    s2 = False
    s3 = False
    c = 0
    for i: plaintext[int] in range(0, N):
        if ((Seq[i] == Syms[3]) and (s2 or s1)):
            c = (c + 1)
        s2 = ((Seq[i] == Syms[2]) and (s1 or s2))
        s1 = (Seq[i] == Syms[1])
    return c
```
### Three-address code CFG
![](count_123_tac_cfg.png)
### SSA
![](count_123_ssa.png)
### SSA ϕ→MUX
![](count_123_ssa_mux.png)
### Dead code elimination
![](count_123_dead_code_elim.png)
### Linear code with loops
```python
def count_123(Seq: shared[list[int]], N: plaintext[int], Syms: shared[list[int]]):
    s1!1 = False
    s2!1 = False
    c!1 = 0
    for i in range(0, N!0):
        s1!2 = Φ(s1!1, s1!3)
        s2!2 = Φ(s2!1, s2!3)
        c!2 = Φ(c!1, c!4)
        !1!2 = (Seq!0[i] == Syms!0[3])
        !2!2 = (s2!2 or s1!2)
        !3!2 = (!1!2 and !2!2)
        c!3 = (c!2 + 1)
        c!4 = MUX(!3!2, c!3, c!2)
        !4!2 = (Seq!0[i] == Syms!0[2])
        !5!2 = (s1!2 or s2!2)
        s2!3 = (!4!2 and !5!2)
        s1!3 = (Seq!0[i] == Syms!0[1])
    return c!2
```
### Dependency graph
![](count_123_dep_graph.png)
### Removal of infeasible edges
![](count_123_remove_infeasible_edges.png)
### Array MUX refinement
```python
def count_123(Seq: shared[list[int]], N: plaintext[int], Syms: shared[list[int]]):
    s1!1 = False
    s2!1 = False
    c!1 = 0
    for i in range(0, N!0):
        s1!2 = Φ(s1!1, s1!3)
        s2!2 = Φ(s2!1, s2!3)
        c!2 = Φ(c!1, c!4)
        !1!2 = (Seq!0[i] == Syms!0[3])
        !2!2 = (s2!2 or s1!2)
        !3!2 = (!1!2 and !2!2)
        c!3 = (c!2 + 1)
        c!4 = MUX(!3!2, c!3, c!2)
        !4!2 = (Seq!0[i] == Syms!0[2])
        !5!2 = (s1!2 or s2!2)
        s2!3 = (!4!2 and !5!2)
        s1!3 = (Seq!0[i] == Syms!0[1])
    return c!2
```
### Array MUX refinement (dependence graph)
![](count_123_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `Seq!0` | `shared[list[int]]` |
| `N!0` | `plaintext[int]` |
| `Syms!0` | `shared[list[int]]` |
| `i` | `plaintext[int]` |
| `s1!3` | `shared[int]` |
| `!4!2` | `shared[int]` |
| `s2!3` | `shared[int]` |
| `!1!2` | `shared[int]` |
| `!3!2` | `shared[int]` |
| `c!1` | `plaintext[int]` |
| `s2!1` | `plaintext[int]` |
| `s1!1` | `plaintext[int]` |
## `histogram`
### Input
```python
import typing

# Array A contains a list of integers i in [1,num_bins]
# Array B is a same-size array, contains number of collected ratings for that bin
# E.g., below we have collected 10 1-star ratings, 1 3-star rating, etc., then 2 more 1-star rating etc.
# A = [0,2,1,0,3,4,2,3]
# B = [10,1,5,2,15,0,10,1000]
# We need to sum up num ratings in each bin to compute a histogram
# 1: 12 0-star ratings                                            
# 2: 5 1-star
# 3: 11 2-star
# 4: 1015 3-star
# 5: 0 4-star                                                            

# This is very similar to the crosstabs app in MOTION
# But we were first to suggest this as a benchmark :).
# requires: len(A) == len(B) = N
def histogram(A: list[int], B: list[int], N, num_bins):
  result: list[int] = []
  # initialize result to 0
  for i in range(num_bins):
    result = result + [0]
  for i in range(num_bins):
    for j in range(N):
      if A[j] == i:
        result[i] = result[i] + B[j]
  return result

A = A = [0,2,1,0,3,4,2,3]
B = [10,1,5,2,15,0,10,1000]
N = len(A)
result = histogram(A,B,N,5)
print(result)

```
### Restricted AST
```python
def histogram(A: shared[list[int]], B: shared[list[int]], N: plaintext[int], num_bins: plaintext[int]):
    result = []
    for i: plaintext[int] in range(0, num_bins):
        result = (result + [0])
    for i: plaintext[int] in range(0, num_bins):
        for j: plaintext[int] in range(0, N):
            if (A[j] == i):
                result[i] = (result[i] + B[j])
    return result
```
### Three-address code CFG
![](histogram_tac_cfg.png)
### SSA
![](histogram_ssa.png)
### SSA ϕ→MUX
![](histogram_ssa_mux.png)
### Dead code elimination
![](histogram_dead_code_elim.png)
### Linear code with loops
```python
def histogram(A: shared[list[int]], B: shared[list[int]], N: plaintext[int], num_bins: plaintext[int]):
    result!1 = []
    for i in range(0, num_bins!0):
        result!2 = Φ(result!1, result!3)
        !1!2 = [0]
        result!3 = (result!2 + !1!2)
    for i in range(0, num_bins!0):
        result!4 = Φ(result!2, result!5)
        for j in range(0, N!0):
            result!5 = Φ(result!4, result!7)
            !2!3 = (A!0[j] == i)
            !3!3 = (result!5[i] + B!0[j])
            result!6 = Update(result!5, i, !3!3)
            result!7 = MUX(!2!3, result!6, result!5)
    return result!4
```
### Dependency graph
![](histogram_dep_graph.png)
### Removal of infeasible edges
![](histogram_remove_infeasible_edges.png)
### Array MUX refinement
```python
def histogram(A: shared[list[int]], B: shared[list[int]], N: plaintext[int], num_bins: plaintext[int]):
    result!1 = []
    for i in range(0, num_bins!0):
        result!2 = Φ(result!1, result!3)
        !1!2 = [0]
        result!3 = (result!2 + !1!2)
    for i in range(0, num_bins!0):
        result!4 = Φ(result!2, result!5)
        for j in range(0, N!0):
            result!5 = Φ(result!4, result!7)
            !2!3 = (A!0[j] == i)
            !3!3 = (result!5[i] + B!0[j])
            result!6 = Update(result!5, i, !3!3)
            result!7 = MUX(!2!3, result!6, result!5)
    return result!4
```
### Array MUX refinement (dependence graph)
![](histogram_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `A!0` | `shared[list[int]]` |
| `B!0` | `shared[list[int]]` |
| `N!0` | `plaintext[int]` |
| `num_bins!0` | `plaintext[int]` |
| `i` | `plaintext[int]` |
| `j` | `plaintext[int]` |
| `!3!3` | `shared[int]` |
| `result!6` | `shared[list[int]]` |
| `result!7` | `shared[list[int]]` |
| `!2!3` | `shared[int]` |
| `!1!2` | `plaintext[list[int]]` |
| `result!1` | `plaintext[list[int]]` |
## `infeasible_edges_example`
### Input
```python
def foo(A, B, C, D, N):
    for i in range(N):
        A[i] = B[i] + 10
        B[i] = A[i] * D[i - 1]
        C[i] = A[i] * D[i - 1]
        D[i] = B[i] * C[i]
    return (A, B, C, D)

```
### Restricted AST
```python
def foo(A: plaintext[int], B: plaintext[int], C: plaintext[int], D: plaintext[int], N: plaintext[int]):
    for i: plaintext[int] in range(0, N):
        A[i] = (B[i] + 10)
        B[i] = (A[i] * D[(i - 1)])
        C[i] = (A[i] * D[(i - 1)])
        D[i] = (B[i] * C[i])
    return (A, B, C, D)
```
### Three-address code CFG
![](infeasible_edges_example_tac_cfg.png)
### SSA
![](infeasible_edges_example_ssa.png)
### SSA ϕ→MUX
![](infeasible_edges_example_ssa_mux.png)
### Dead code elimination
![](infeasible_edges_example_dead_code_elim.png)
### Linear code with loops
```python
def foo(A: plaintext[int], B: plaintext[int], C: plaintext[int], D: plaintext[int], N: plaintext[int]):
    for i in range(0, N!0):
        A!1 = Φ(A!0, A!2)
        B!1 = Φ(B!0, B!2)
        C!1 = Φ(C!0, C!2)
        D!1 = Φ(D!0, D!2)
        !1!2 = (B!1[i] + 10)
        A!2 = Update(A!1, i, !1!2)
        !2!2 = (A!2[i] * D!1[(i - 1)])
        B!2 = Update(B!1, i, !2!2)
        !3!2 = (A!2[i] * D!1[(i - 1)])
        C!2 = Update(C!1, i, !3!2)
        !4!2 = (B!2[i] * C!2[i])
        D!2 = Update(D!1, i, !4!2)
    !5!1 = (A!1, B!1, C!1, D!1)
    return !5!1
```
### Dependency graph
![](infeasible_edges_example_dep_graph.png)
### Removal of infeasible edges
![](infeasible_edges_example_remove_infeasible_edges.png)
### Array MUX refinement
```python
def foo(A: plaintext[int], B: plaintext[int], C: plaintext[int], D: plaintext[int], N: plaintext[int]):
    for i in range(0, N!0):
        A!1 = Φ(A!0, A!2)
        B!1 = Φ(B!0, B!2)
        C!1 = Φ(C!0, C!2)
        D!1 = Φ(D!0, D!2)
        !1!2 = (B!1[i] + 10)
        A!2 = Update(A!1, i, !1!2)
        !2!2 = (A!2[i] * D!1[(i - 1)])
        B!2 = Update(B!1, i, !2!2)
        !3!2 = (A!2[i] * D!1[(i - 1)])
        C!2 = Update(C!1, i, !3!2)
        !4!2 = (B!2[i] * C!2[i])
        D!2 = Update(D!1, i, !4!2)
    !5!1 = (A!1, B!1, C!1, D!1)
    return !5!1
```
### Array MUX refinement (dependence graph)
![](infeasible_edges_example_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `A!0` | `plaintext[int]` |
| `B!0` | `plaintext[int]` |
| `C!0` | `plaintext[int]` |
| `D!0` | `plaintext[int]` |
| `N!0` | `plaintext[int]` |
| `i` | `plaintext[int]` |
## `inner_product`
### Input
```python
import typing

def ip(A: list[int], B: list[int], N):
  sum = 0
  for i in range(0,N):
    temp = A[i]*B[i]
    sum = sum + temp
  return sum

A = [1,2,3]
B = [4,5,6]
sum = ip(A,B,3)
print(sum)

```
### Restricted AST
```python
def ip(A: shared[list[int]], B: shared[list[int]], N: plaintext[int]):
    sum = 0
    for i: plaintext[int] in range(0, N):
        temp = (A[i] * B[i])
        sum = (sum + temp)
    return sum
```
### Three-address code CFG
![](inner_product_tac_cfg.png)
### SSA
![](inner_product_ssa.png)
### SSA ϕ→MUX
![](inner_product_ssa_mux.png)
### Dead code elimination
![](inner_product_dead_code_elim.png)
### Linear code with loops
```python
def ip(A: shared[list[int]], B: shared[list[int]], N: plaintext[int]):
    sum!1 = 0
    for i in range(0, N!0):
        sum!2 = Φ(sum!1, sum!3)
        temp!2 = (A!0[i] * B!0[i])
        sum!3 = (sum!2 + temp!2)
    return sum!2
```
### Dependency graph
![](inner_product_dep_graph.png)
### Removal of infeasible edges
![](inner_product_remove_infeasible_edges.png)
### Array MUX refinement
```python
def ip(A: shared[list[int]], B: shared[list[int]], N: plaintext[int]):
    sum!1 = 0
    for i in range(0, N!0):
        sum!2 = Φ(sum!1, sum!3)
        temp!2 = (A!0[i] * B!0[i])
        sum!3 = (sum!2 + temp!2)
    return sum!2
```
### Array MUX refinement (dependence graph)
![](inner_product_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `A!0` | `shared[list[int]]` |
| `B!0` | `shared[list[int]]` |
| `N!0` | `plaintext[int]` |
| `i` | `plaintext[int]` |
| `temp!2` | `shared[int]` |
| `sum!3` | `shared[int]` |
| `sum!1` | `plaintext[int]` |
## `longest_102`
### Input
```python
def longest_102(Seq: list[int], N, Syms: list[int]):
    """
    Computes the length of the largest instance of regex a(b*)c in a provided sequence.
    Syms is a list of form [a, b, c].
    """
    s0 = False

    max_len = 0
    length = 0

    for i in range(0, N):
        s1 = s0 and (Seq[i] == Syms[2])
        s0 = (Seq[i] == Syms[1]) or (s0 and (Seq[i] == Syms[0]))

        if s1 or s0:
            length = length + 1
        else:
            length = 0

        if s1 and max_len < length:
            max_len = length

    return max_len


seq = [1, 0, 2, 1, 0, 0, 2, 1, 2, 2]
longest_102_len = longest_102(seq, len(seq), [1, 0, 2])
print(longest_102_len)

```
### Restricted AST
```python
def longest_102(Seq: shared[list[int]], N: plaintext[int], Syms: shared[list[int]]):
    s0 = False
    max_len = 0
    length = 0
    for i: plaintext[int] in range(0, N):
        s1 = (s0 and (Seq[i] == Syms[2]))
        s0 = ((Seq[i] == Syms[1]) or (s0 and (Seq[i] == Syms[0])))
        if (s1 or s0):
            length = (length + 1)
        else:
            length = 0
        if (s1 and (max_len < length)):
            max_len = length
    return max_len
```
### Three-address code CFG
![](longest_102_tac_cfg.png)
### SSA
![](longest_102_ssa.png)
### SSA ϕ→MUX
![](longest_102_ssa_mux.png)
### Dead code elimination
![](longest_102_dead_code_elim.png)
### Linear code with loops
```python
def longest_102(Seq: shared[list[int]], N: plaintext[int], Syms: shared[list[int]]):
    s0!1 = False
    max_len!1 = 0
    length!1 = 0
    for i in range(0, N!0):
        s0!2 = Φ(s0!1, s0!3)
        max_len!2 = Φ(max_len!1, max_len!4)
        length!2 = Φ(length!1, length!5)
        !1!2 = (Seq!0[i] == Syms!0[2])
        s1!2 = (s0!2 and !1!2)
        !2!2 = (Seq!0[i] == Syms!0[1])
        !4!2 = (Seq!0[i] == Syms!0[0])
        !5!2 = (s0!2 and !4!2)
        s0!3 = (!2!2 or !5!2)
        !6!2 = (s1!2 or s0!3)
        length!4 = 0
        length!3 = (length!2 + 1)
        length!5 = MUX(!6!2, length!3, length!4)
        !7!2 = (max_len!2 < length!5)
        !8!2 = (s1!2 and !7!2)
        max_len!3 = length!5
        max_len!4 = MUX(!8!2, max_len!3, max_len!2)
    return max_len!2
```
### Dependency graph
![](longest_102_dep_graph.png)
### Removal of infeasible edges
![](longest_102_remove_infeasible_edges.png)
### Array MUX refinement
```python
def longest_102(Seq: shared[list[int]], N: plaintext[int], Syms: shared[list[int]]):
    s0!1 = False
    max_len!1 = 0
    length!1 = 0
    for i in range(0, N!0):
        s0!2 = Φ(s0!1, s0!3)
        max_len!2 = Φ(max_len!1, max_len!4)
        length!2 = Φ(length!1, length!5)
        !1!2 = (Seq!0[i] == Syms!0[2])
        s1!2 = (s0!2 and !1!2)
        !2!2 = (Seq!0[i] == Syms!0[1])
        !4!2 = (Seq!0[i] == Syms!0[0])
        !5!2 = (s0!2 and !4!2)
        s0!3 = (!2!2 or !5!2)
        !6!2 = (s1!2 or s0!3)
        length!4 = 0
        length!3 = (length!2 + 1)
        length!5 = MUX(!6!2, length!3, length!4)
        !7!2 = (max_len!2 < length!5)
        !8!2 = (s1!2 and !7!2)
        max_len!3 = length!5
        max_len!4 = MUX(!8!2, max_len!3, max_len!2)
    return max_len!2
```
### Array MUX refinement (dependence graph)
![](longest_102_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `Seq!0` | `shared[list[int]]` |
| `N!0` | `plaintext[int]` |
| `Syms!0` | `shared[list[int]]` |
| `i` | `plaintext[int]` |
| `length!4` | `plaintext[int]` |
| `length!5` | `shared[int]` |
| `max_len!3` | `shared[int]` |
| `max_len!4` | `shared[int]` |
| `!7!2` | `shared[int]` |
| `!8!2` | `shared[int]` |
| `!4!2` | `shared[int]` |
| `!5!2` | `shared[int]` |
| `s0!3` | `shared[int]` |
| `!6!2` | `shared[int]` |
| `!2!2` | `shared[int]` |
| `!1!2` | `shared[int]` |
| `s1!2` | `shared[int]` |
| `length!1` | `plaintext[int]` |
| `max_len!1` | `plaintext[int]` |
| `s0!1` | `plaintext[int]` |
## `longest_1s`
### Input
```python
def longest_1s(Seq: list[int], N, Sym: int):
    """
    Computes length of the longest sequence of form (a*).
    Sym is the integer a.
    """

    max_length = 0
    length = 0

    for i in range(1, N):
        if Seq[i] == Sym:
            length = length + 1
        else:
            length = 0

        if length > max_length:
            max_length = length

    return max_length


seq = [0, 0, 1, 1, 1, 1, 0, 1, 0]
longest_1s_len = longest_1s(seq, len(seq), 1)
print(longest_1s_len)

```
### Restricted AST
```python
def longest_1s(Seq: shared[list[int]], N: plaintext[int], Sym: shared[int]):
    max_length = 0
    length = 0
    for i: plaintext[int] in range(1, N):
        if (Seq[i] == Sym):
            length = (length + 1)
        else:
            length = 0
        if (length > max_length):
            max_length = length
    return max_length
```
### Three-address code CFG
![](longest_1s_tac_cfg.png)
### SSA
![](longest_1s_ssa.png)
### SSA ϕ→MUX
![](longest_1s_ssa_mux.png)
### Dead code elimination
![](longest_1s_dead_code_elim.png)
### Linear code with loops
```python
def longest_1s(Seq: shared[list[int]], N: plaintext[int], Sym: shared[int]):
    max_length!1 = 0
    length!1 = 0
    for i in range(1, N!0):
        max_length!2 = Φ(max_length!1, max_length!4)
        length!2 = Φ(length!1, length!5)
        !1!2 = (Seq!0[i] == Sym!0)
        length!4 = 0
        length!3 = (length!2 + 1)
        length!5 = MUX(!1!2, length!3, length!4)
        !2!2 = (length!5 > max_length!2)
        max_length!3 = length!5
        max_length!4 = MUX(!2!2, max_length!3, max_length!2)
    return max_length!2
```
### Dependency graph
![](longest_1s_dep_graph.png)
### Removal of infeasible edges
![](longest_1s_remove_infeasible_edges.png)
### Array MUX refinement
```python
def longest_1s(Seq: shared[list[int]], N: plaintext[int], Sym: shared[int]):
    max_length!1 = 0
    length!1 = 0
    for i in range(1, N!0):
        max_length!2 = Φ(max_length!1, max_length!4)
        length!2 = Φ(length!1, length!5)
        !1!2 = (Seq!0[i] == Sym!0)
        length!4 = 0
        length!3 = (length!2 + 1)
        length!5 = MUX(!1!2, length!3, length!4)
        !2!2 = (length!5 > max_length!2)
        max_length!3 = length!5
        max_length!4 = MUX(!2!2, max_length!3, max_length!2)
    return max_length!2
```
### Array MUX refinement (dependence graph)
![](longest_1s_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `Seq!0` | `shared[list[int]]` |
| `N!0` | `plaintext[int]` |
| `Sym!0` | `shared[int]` |
| `i` | `plaintext[int]` |
| `length!4` | `plaintext[int]` |
| `length!5` | `shared[int]` |
| `max_length!3` | `shared[int]` |
| `max_length!4` | `shared[int]` |
| `!2!2` | `shared[int]` |
| `!1!2` | `shared[int]` |
| `length!1` | `plaintext[int]` |
| `max_length!1` | `plaintext[int]` |
## `longest_even_0`
### Input
```python
def longest_even_0(Seq: list[int], N, Sym: int):
    """
    Computes the length of the longest regex of form (a*) which has an even length
    Sym is the symbol a
    """

    current_length = 0
    max_length = 0

    for i in range(1, N):
        if Seq[i] == Sym:
            current_length = current_length + 1
        else:
            current_length = 0

        tmp_max_len = max_length
        if current_length > max_length:
            tmp_max_len = current_length

        if tmp_max_len % 2 == 0:
            max_length = tmp_max_len

    return max_length

```
### Restricted AST
```python
def longest_even_0(Seq: shared[list[int]], N: plaintext[int], Sym: shared[int]):
    current_length = 0
    max_length = 0
    for i: plaintext[int] in range(1, N):
        if (Seq[i] == Sym):
            current_length = (current_length + 1)
        else:
            current_length = 0
        tmp_max_len = max_length
        if (current_length > max_length):
            tmp_max_len = current_length
        if ((tmp_max_len % 2) == 0):
            max_length = tmp_max_len
    return max_length
```
### Three-address code CFG
![](longest_even_0_tac_cfg.png)
### SSA
![](longest_even_0_ssa.png)
### SSA ϕ→MUX
![](longest_even_0_ssa_mux.png)
### Dead code elimination
![](longest_even_0_dead_code_elim.png)
### Linear code with loops
```python
def longest_even_0(Seq: shared[list[int]], N: plaintext[int], Sym: shared[int]):
    current_length!1 = 0
    max_length!1 = 0
    for i in range(1, N!0):
        current_length!2 = Φ(current_length!1, current_length!5)
        max_length!2 = Φ(max_length!1, max_length!4)
        !1!2 = (Seq!0[i] == Sym!0)
        current_length!4 = 0
        current_length!3 = (current_length!2 + 1)
        current_length!5 = MUX(!1!2, current_length!3, current_length!4)
        tmp_max_len!2 = max_length!2
        !2!2 = (current_length!5 > max_length!2)
        tmp_max_len!3 = current_length!5
        tmp_max_len!4 = MUX(!2!2, tmp_max_len!3, tmp_max_len!2)
        !3!2 = (tmp_max_len!4 % 2)
        !4!2 = (!3!2 == 0)
        max_length!3 = tmp_max_len!4
        max_length!4 = MUX(!4!2, max_length!3, max_length!2)
    return max_length!2
```
### Dependency graph
![](longest_even_0_dep_graph.png)
### Removal of infeasible edges
![](longest_even_0_remove_infeasible_edges.png)
### Array MUX refinement
```python
def longest_even_0(Seq: shared[list[int]], N: plaintext[int], Sym: shared[int]):
    current_length!1 = 0
    max_length!1 = 0
    for i in range(1, N!0):
        current_length!2 = Φ(current_length!1, current_length!5)
        max_length!2 = Φ(max_length!1, max_length!4)
        !1!2 = (Seq!0[i] == Sym!0)
        current_length!4 = 0
        current_length!3 = (current_length!2 + 1)
        current_length!5 = MUX(!1!2, current_length!3, current_length!4)
        tmp_max_len!2 = max_length!2
        !2!2 = (current_length!5 > max_length!2)
        tmp_max_len!3 = current_length!5
        tmp_max_len!4 = MUX(!2!2, tmp_max_len!3, tmp_max_len!2)
        !3!2 = (tmp_max_len!4 % 2)
        !4!2 = (!3!2 == 0)
        max_length!3 = tmp_max_len!4
        max_length!4 = MUX(!4!2, max_length!3, max_length!2)
    return max_length!2
```
### Array MUX refinement (dependence graph)
![](longest_even_0_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `Seq!0` | `shared[list[int]]` |
| `N!0` | `plaintext[int]` |
| `Sym!0` | `shared[int]` |
| `i` | `plaintext[int]` |
| `current_length!4` | `plaintext[int]` |
| `current_length!5` | `shared[int]` |
| `tmp_max_len!3` | `shared[int]` |
| `tmp_max_len!4` | `shared[int]` |
| `max_length!3` | `shared[int]` |
| `max_length!4` | `shared[int]` |
| `!3!2` | `shared[int]` |
| `!4!2` | `shared[int]` |
| `!2!2` | `shared[int]` |
| `!1!2` | `shared[int]` |
| `max_length!1` | `plaintext[int]` |
| `current_length!1` | `plaintext[int]` |
## `longest_odd_10`
### Input
```python
def longest_odd_10(Seq: list[int], N, Syms: list[int]):
    """
    Computes the length of the longest regex of form (ab)* which has an odd length
    Syms is the list [a, b]
    """

    current_length = 0
    max_length = 0

    s2 = False

    for i in range(0, N):
        s1 = s2 and (Seq[i] == Syms[1])

        if s1:
            current_length = current_length + 1
        elif not s2:
            current_length = 0

        if (current_length % 2 == 1) and (current_length > max_length):
            max_length = current_length

        s2 = Seq[i] == Syms[0]

    return max_length

```
### Restricted AST
```python
def longest_odd_10(Seq: shared[list[int]], N: plaintext[int], Syms: shared[list[int]]):
    current_length = 0
    max_length = 0
    s2 = False
    for i: plaintext[int] in range(0, N):
        s1 = (s2 and (Seq[i] == Syms[1]))
        if s1:
            current_length = (current_length + 1)
        else:
            if not s2:
                current_length = 0
        if (((current_length % 2) == 1) and (current_length > max_length)):
            max_length = current_length
        s2 = (Seq[i] == Syms[0])
    return max_length
```
### Three-address code CFG
![](longest_odd_10_tac_cfg.png)
### SSA
![](longest_odd_10_ssa.png)
### SSA ϕ→MUX
![](longest_odd_10_ssa_mux.png)
### Dead code elimination
![](longest_odd_10_dead_code_elim.png)
### Linear code with loops
```python
def longest_odd_10(Seq: shared[list[int]], N: plaintext[int], Syms: shared[list[int]]):
    current_length!1 = 0
    max_length!1 = 0
    s2!1 = False
    for i in range(0, N!0):
        current_length!2 = Φ(current_length!1, current_length!6)
        max_length!2 = Φ(max_length!1, max_length!4)
        s2!2 = Φ(s2!1, s2!3)
        !1!2 = (Seq!0[i] == Syms!0[1])
        s1!2 = (s2!2 and !1!2)
        !2!2 = not s2!2
        current_length!4 = 0
        current_length!5 = MUX(!2!2, current_length!4, current_length!2)
        current_length!3 = (current_length!2 + 1)
        current_length!6 = MUX(s1!2, current_length!3, current_length!5)
        !4!2 = (current_length!6 % 2)
        !5!2 = (!4!2 == 1)
        !6!2 = (current_length!6 > max_length!2)
        !7!2 = (!5!2 and !6!2)
        max_length!3 = current_length!6
        max_length!4 = MUX(!7!2, max_length!3, max_length!2)
        s2!3 = (Seq!0[i] == Syms!0[0])
    return max_length!2
```
### Dependency graph
![](longest_odd_10_dep_graph.png)
### Removal of infeasible edges
![](longest_odd_10_remove_infeasible_edges.png)
### Array MUX refinement
```python
def longest_odd_10(Seq: shared[list[int]], N: plaintext[int], Syms: shared[list[int]]):
    current_length!1 = 0
    max_length!1 = 0
    s2!1 = False
    for i in range(0, N!0):
        current_length!2 = Φ(current_length!1, current_length!6)
        max_length!2 = Φ(max_length!1, max_length!4)
        s2!2 = Φ(s2!1, s2!3)
        !1!2 = (Seq!0[i] == Syms!0[1])
        s1!2 = (s2!2 and !1!2)
        !2!2 = not s2!2
        current_length!4 = 0
        current_length!5 = MUX(!2!2, current_length!4, current_length!2)
        current_length!3 = (current_length!2 + 1)
        current_length!6 = MUX(s1!2, current_length!3, current_length!5)
        !4!2 = (current_length!6 % 2)
        !5!2 = (!4!2 == 1)
        !6!2 = (current_length!6 > max_length!2)
        !7!2 = (!5!2 and !6!2)
        max_length!3 = current_length!6
        max_length!4 = MUX(!7!2, max_length!3, max_length!2)
        s2!3 = (Seq!0[i] == Syms!0[0])
    return max_length!2
```
### Array MUX refinement (dependence graph)
![](longest_odd_10_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `Seq!0` | `shared[list[int]]` |
| `N!0` | `plaintext[int]` |
| `Syms!0` | `shared[list[int]]` |
| `i` | `plaintext[int]` |
| `s2!3` | `shared[int]` |
| `current_length!4` | `plaintext[int]` |
| `current_length!5` | `shared[int]` |
| `current_length!6` | `shared[int]` |
| `max_length!3` | `shared[int]` |
| `max_length!4` | `shared[int]` |
| `!6!2` | `shared[int]` |
| `!7!2` | `shared[int]` |
| `!4!2` | `shared[int]` |
| `!5!2` | `shared[int]` |
| `!1!2` | `shared[int]` |
| `s1!2` | `shared[int]` |
| `s2!1` | `plaintext[int]` |
| `max_length!1` | `plaintext[int]` |
| `current_length!1` | `plaintext[int]` |
## `max_dist_between_syms`
### Input
```python
def max_dist_between_syms(Seq: list[int], N, Sym: int):
    max_dist = 0
    current_dist = 0
    for i in range(0, N):
        if not (Seq[i] == Sym):
            current_dist = current_dist + 1
        else:
            current_dist = 0

        if current_dist > max_dist:
            max_dist = current_dist
    return max_dist


seq = [1, 2, 1, 1, 2, 3, 4, 1]
max_dist = max_dist_between_syms(seq, len(seq), 1)
print(max_dist)

```
### Restricted AST
```python
def max_dist_between_syms(Seq: shared[list[int]], N: plaintext[int], Sym: shared[int]):
    max_dist = 0
    current_dist = 0
    for i: plaintext[int] in range(0, N):
        if not (Seq[i] == Sym):
            current_dist = (current_dist + 1)
        else:
            current_dist = 0
        if (current_dist > max_dist):
            max_dist = current_dist
    return max_dist
```
### Three-address code CFG
![](max_dist_between_syms_tac_cfg.png)
### SSA
![](max_dist_between_syms_ssa.png)
### SSA ϕ→MUX
![](max_dist_between_syms_ssa_mux.png)
### Dead code elimination
![](max_dist_between_syms_dead_code_elim.png)
### Linear code with loops
```python
def max_dist_between_syms(Seq: shared[list[int]], N: plaintext[int], Sym: shared[int]):
    max_dist!1 = 0
    current_dist!1 = 0
    for i in range(0, N!0):
        max_dist!2 = Φ(max_dist!1, max_dist!4)
        current_dist!2 = Φ(current_dist!1, current_dist!5)
        !1!2 = (Seq!0[i] == Sym!0)
        !2!2 = not !1!2
        current_dist!4 = 0
        current_dist!3 = (current_dist!2 + 1)
        current_dist!5 = MUX(!2!2, current_dist!3, current_dist!4)
        !3!2 = (current_dist!5 > max_dist!2)
        max_dist!3 = current_dist!5
        max_dist!4 = MUX(!3!2, max_dist!3, max_dist!2)
    return max_dist!2
```
### Dependency graph
![](max_dist_between_syms_dep_graph.png)
### Removal of infeasible edges
![](max_dist_between_syms_remove_infeasible_edges.png)
### Array MUX refinement
```python
def max_dist_between_syms(Seq: shared[list[int]], N: plaintext[int], Sym: shared[int]):
    max_dist!1 = 0
    current_dist!1 = 0
    for i in range(0, N!0):
        max_dist!2 = Φ(max_dist!1, max_dist!4)
        current_dist!2 = Φ(current_dist!1, current_dist!5)
        !1!2 = (Seq!0[i] == Sym!0)
        !2!2 = not !1!2
        current_dist!4 = 0
        current_dist!3 = (current_dist!2 + 1)
        current_dist!5 = MUX(!2!2, current_dist!3, current_dist!4)
        !3!2 = (current_dist!5 > max_dist!2)
        max_dist!3 = current_dist!5
        max_dist!4 = MUX(!3!2, max_dist!3, max_dist!2)
    return max_dist!2
```
### Array MUX refinement (dependence graph)
![](max_dist_between_syms_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `Seq!0` | `shared[list[int]]` |
| `N!0` | `plaintext[int]` |
| `Sym!0` | `shared[int]` |
| `i` | `plaintext[int]` |
| `current_dist!4` | `plaintext[int]` |
| `current_dist!5` | `shared[int]` |
| `max_dist!3` | `shared[int]` |
| `max_dist!4` | `shared[int]` |
| `!3!2` | `shared[int]` |
| `!1!2` | `shared[int]` |
| `!2!2` | `shared[int]` |
| `current_dist!1` | `plaintext[int]` |
| `max_dist!1` | `plaintext[int]` |
## `max_sum_between_syms`
### Input
```python
def max_sum_between_syms(Seq: list[int], N, Sym: int):
    max_sum = 0
    current_sum = 0
    for i in range(0, N):
        if not (Seq[i] == Sym):
            current_sum = current_sum + Seq[i]
        else:
            current_sum = 0

        if current_sum > max_sum:
            max_sum = current_sum
    return max_sum


seq = [1, 2, 1, 1, 2, 3, 4, 1]
max_sum = max_sum_between_syms(seq, len(seq), 1)
print(max_sum)

```
### Restricted AST
```python
def max_sum_between_syms(Seq: shared[list[int]], N: plaintext[int], Sym: shared[int]):
    max_sum = 0
    current_sum = 0
    for i: plaintext[int] in range(0, N):
        if not (Seq[i] == Sym):
            current_sum = (current_sum + Seq[i])
        else:
            current_sum = 0
        if (current_sum > max_sum):
            max_sum = current_sum
    return max_sum
```
### Three-address code CFG
![](max_sum_between_syms_tac_cfg.png)
### SSA
![](max_sum_between_syms_ssa.png)
### SSA ϕ→MUX
![](max_sum_between_syms_ssa_mux.png)
### Dead code elimination
![](max_sum_between_syms_dead_code_elim.png)
### Linear code with loops
```python
def max_sum_between_syms(Seq: shared[list[int]], N: plaintext[int], Sym: shared[int]):
    max_sum!1 = 0
    current_sum!1 = 0
    for i in range(0, N!0):
        max_sum!2 = Φ(max_sum!1, max_sum!4)
        current_sum!2 = Φ(current_sum!1, current_sum!5)
        !1!2 = (Seq!0[i] == Sym!0)
        !2!2 = not !1!2
        current_sum!4 = 0
        current_sum!3 = (current_sum!2 + Seq!0[i])
        current_sum!5 = MUX(!2!2, current_sum!3, current_sum!4)
        !3!2 = (current_sum!5 > max_sum!2)
        max_sum!3 = current_sum!5
        max_sum!4 = MUX(!3!2, max_sum!3, max_sum!2)
    return max_sum!2
```
### Dependency graph
![](max_sum_between_syms_dep_graph.png)
### Removal of infeasible edges
![](max_sum_between_syms_remove_infeasible_edges.png)
### Array MUX refinement
```python
def max_sum_between_syms(Seq: shared[list[int]], N: plaintext[int], Sym: shared[int]):
    max_sum!1 = 0
    current_sum!1 = 0
    for i in range(0, N!0):
        max_sum!2 = Φ(max_sum!1, max_sum!4)
        current_sum!2 = Φ(current_sum!1, current_sum!5)
        !1!2 = (Seq!0[i] == Sym!0)
        !2!2 = not !1!2
        current_sum!4 = 0
        current_sum!3 = (current_sum!2 + Seq!0[i])
        current_sum!5 = MUX(!2!2, current_sum!3, current_sum!4)
        !3!2 = (current_sum!5 > max_sum!2)
        max_sum!3 = current_sum!5
        max_sum!4 = MUX(!3!2, max_sum!3, max_sum!2)
    return max_sum!2
```
### Array MUX refinement (dependence graph)
![](max_sum_between_syms_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `Seq!0` | `shared[list[int]]` |
| `N!0` | `plaintext[int]` |
| `Sym!0` | `shared[int]` |
| `i` | `plaintext[int]` |
| `current_sum!3` | `shared[int]` |
| `current_sum!5` | `shared[int]` |
| `max_sum!3` | `shared[int]` |
| `max_sum!4` | `shared[int]` |
| `!3!2` | `shared[int]` |
| `current_sum!4` | `plaintext[int]` |
| `!1!2` | `shared[int]` |
| `!2!2` | `shared[int]` |
| `current_sum!1` | `plaintext[int]` |
| `max_sum!1` | `plaintext[int]` |
## `minimal_points`
### Input
```python
def minimal_points(X_coords: list[int], Y_coords: list[int], N):
    min_X: list[int] = []
    min_Y: list[int] = []

    for i in range(0, N):
        bx = False
        for j in range(0, N):
            bx = bx or (X_coords[j] < X_coords[i] and Y_coords[j] < Y_coords[i])
        if not bx:
            min_X = min_X + [X_coords[i]]
            min_Y = min_Y + [Y_coords[i]]

    return (min_X, min_Y)


X_coords = [1, 2, 3]
Y_coords = [4, 5, 6]
min_x, min_y = minimal_points(X_coords, Y_coords, len(X_coords))
print(min_x)
print(min_y)

```
### Restricted AST
```python
def minimal_points(X_coords: shared[list[int]], Y_coords: shared[list[int]], N: plaintext[int]):
    min_X = []
    min_Y = []
    for i: plaintext[int] in range(0, N):
        bx = False
        for j: plaintext[int] in range(0, N):
            bx = (bx or ((X_coords[j] < X_coords[i]) and (Y_coords[j] < Y_coords[i])))
        if not bx:
            min_X = (min_X + [X_coords[i]])
            min_Y = (min_Y + [Y_coords[i]])
    return (min_X, min_Y)
```
### Three-address code CFG
![](minimal_points_tac_cfg.png)
### SSA
![](minimal_points_ssa.png)
### SSA ϕ→MUX
![](minimal_points_ssa_mux.png)
### Dead code elimination
![](minimal_points_dead_code_elim.png)
### Linear code with loops
```python
def minimal_points(X_coords: shared[list[int]], Y_coords: shared[list[int]], N: plaintext[int]):
    min_X!1 = []
    min_Y!1 = []
    for i in range(0, N!0):
        min_X!2 = Φ(min_X!1, min_X!4)
        min_Y!2 = Φ(min_Y!1, min_Y!4)
        bx!2 = False
        for j in range(0, N!0):
            bx!3 = Φ(bx!2, bx!4)
            !3!3 = (X_coords!0[j] < X_coords!0[i])
            !4!3 = (Y_coords!0[j] < Y_coords!0[i])
            !5!3 = (!3!3 and !4!3)
            bx!4 = (bx!3 or !5!3)
        !6!2 = not bx!3
        !8!2 = X_coords!0[i]
        !9!2 = [!8!2]
        min_X!3 = (min_X!2 + !9!2)
        !11!2 = Y_coords!0[i]
        !12!2 = [!11!2]
        min_Y!3 = (min_Y!2 + !12!2)
        min_X!4 = MUX(!6!2, min_X!3, min_X!2)
        min_Y!4 = MUX(!6!2, min_Y!3, min_Y!2)
    !13!1 = (min_X!2, min_Y!2)
    return !13!1
```
### Dependency graph
![](minimal_points_dep_graph.png)
### Removal of infeasible edges
![](minimal_points_remove_infeasible_edges.png)
### Array MUX refinement
```python
def minimal_points(X_coords: shared[list[int]], Y_coords: shared[list[int]], N: plaintext[int]):
    min_X!1 = []
    min_Y!1 = []
    for i in range(0, N!0):
        min_X!2 = Φ(min_X!1, min_X!4)
        min_Y!2 = Φ(min_Y!1, min_Y!4)
        bx!2 = False
        for j in range(0, N!0):
            bx!3 = Φ(bx!2, bx!4)
            !3!3 = (X_coords!0[j] < X_coords!0[i])
            !4!3 = (Y_coords!0[j] < Y_coords!0[i])
            !5!3 = (!3!3 and !4!3)
            bx!4 = (bx!3 or !5!3)
        !6!2 = not bx!3
        !8!2 = X_coords!0[i]
        !9!2 = [!8!2]
        min_X!3 = (min_X!2 + !9!2)
        !11!2 = Y_coords!0[i]
        !12!2 = [!11!2]
        min_Y!3 = (min_Y!2 + !12!2)
        min_X!4 = MUX(!6!2, min_X!3, min_X!2)
        min_Y!4 = MUX(!6!2, min_Y!3, min_Y!2)
    !13!1 = (min_X!2, min_Y!2)
    return !13!1
```
### Array MUX refinement (dependence graph)
![](minimal_points_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `X_coords!0` | `shared[list[int]]` |
| `Y_coords!0` | `shared[list[int]]` |
| `N!0` | `plaintext[int]` |
| `i` | `plaintext[int]` |
| `j` | `plaintext[int]` |
| `!11!2` | `shared[int]` |
| `!12!2` | `shared[list[int]]` |
| `min_Y!3` | `shared[list[int]]` |
| `min_Y!4` | `shared[list[int]]` |
| `!8!2` | `shared[int]` |
| `!9!2` | `shared[list[int]]` |
| `min_X!3` | `shared[list[int]]` |
| `min_X!4` | `shared[list[int]]` |
| `!4!3` | `shared[int]` |
| `!5!3` | `shared[int]` |
| `bx!4` | `shared[int]` |
| `!3!3` | `shared[int]` |
| `bx!2` | `plaintext[int]` |
| `min_Y!1` | `plaintext[list[int]]` |
| `min_X!1` | `plaintext[list[int]]` |
## `psi`
### Input
```python
import typing

# returns a list[int] which is the intersection 
# of privite sets of integers A and B
# requires: no repetition of elements in either A or B
# requires: len(A) = SA, len(B) = SB
def psi(A: list[int], SA, B: list[int], SB) -> list[int]:
  dummy : int = 0
  result: list[int] = []
  for i in range(0,SA):
    flag : Bool = False
    for j in range(0,SB):
      if A[i] == B[j]:
        flag = True
    val : int = dummy
    if flag:
      val : int = A[i]
    #overloaded +. This is append actually.
    result = result + [val]
  return result

A = [4,2,3,1,10]
B = [2,10,3,4,5,6,7]
intersect = psi(A,5,B,7)
print(intersect)


```
### Restricted AST
```python
def psi(A: shared[list[int]], SA: plaintext[int], B: shared[list[int]], SB: plaintext[int]):
    dummy = 0
    result = []
    for i: plaintext[int] in range(0, SA):
        flag = False
        for j: plaintext[int] in range(0, SB):
            if (A[i] == B[j]):
                flag = True
        val = dummy
        if flag:
            val = A[i]
        result = (result + [val])
    return result
```
### Three-address code CFG
![](psi_tac_cfg.png)
### SSA
![](psi_ssa.png)
### SSA ϕ→MUX
![](psi_ssa_mux.png)
### Dead code elimination
![](psi_dead_code_elim.png)
### Linear code with loops
```python
def psi(A: shared[list[int]], SA: plaintext[int], B: shared[list[int]], SB: plaintext[int]):
    dummy!1 = 0
    result!1 = []
    for i in range(0, SA!0):
        result!2 = Φ(result!1, result!3)
        flag!2 = False
        for j in range(0, SB!0):
            flag!3 = Φ(flag!2, flag!5)
            !1!3 = (A!0[i] == B!0[j])
            flag!4 = True
            flag!5 = MUX(!1!3, flag!4, flag!3)
        val!2 = dummy!1
        val!3 = A!0[i]
        val!4 = MUX(flag!3, val!3, val!2)
        !2!2 = [val!4]
        result!3 = (result!2 + !2!2)
    return result!2
```
### Dependency graph
![](psi_dep_graph.png)
### Removal of infeasible edges
![](psi_remove_infeasible_edges.png)
### Array MUX refinement
```python
def psi(A: shared[list[int]], SA: plaintext[int], B: shared[list[int]], SB: plaintext[int]):
    dummy!1 = 0
    result!1 = []
    for i in range(0, SA!0):
        result!2 = Φ(result!1, result!3)
        flag!2 = False
        for j in range(0, SB!0):
            flag!3 = Φ(flag!2, flag!5)
            !1!3 = (A!0[i] == B!0[j])
            flag!4 = True
            flag!5 = MUX(!1!3, flag!4, flag!3)
        val!2 = dummy!1
        val!3 = A!0[i]
        val!4 = MUX(flag!3, val!3, val!2)
        !2!2 = [val!4]
        result!3 = (result!2 + !2!2)
    return result!2
```
### Array MUX refinement (dependence graph)
![](psi_array_mux_refinement_dep_graph.png)
### Type environment
| Variable | Type |
| - | - |
| `A!0` | `shared[list[int]]` |
| `SA!0` | `plaintext[int]` |
| `B!0` | `shared[list[int]]` |
| `SB!0` | `plaintext[int]` |
| `i` | `plaintext[int]` |
| `j` | `plaintext[int]` |
| `val!3` | `shared[int]` |
| `val!4` | `shared[int]` |
| `!2!2` | `shared[list[int]]` |
| `result!3` | `shared[list[int]]` |
| `flag!4` | `plaintext[int]` |
| `flag!5` | `shared[int]` |
| `!1!3` | `shared[int]` |
| `flag!2` | `plaintext[int]` |
| `result!1` | `plaintext[list[int]]` |
| `dummy!1` | `plaintext[int]` |
| `val!2` | `plaintext[int]` |
