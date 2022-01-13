def biometric_matching_vectorized(D, N, C:list[int], C_sqr_sum:int, two_C:list[int], S: List[int], S_sqr_sum: list[int]):
  """
  Computes biometric matching

  This is vectorized version of `biometric_matching_fast`. NOTE: This code is for illustration purposes only. It will not run as-is
  because python does not have the SIMD instructions we assume our backend to support.

  See docs for `biometric_matching_fast` for a description of parameters

  """

  two_a_b: list[int] = [0] * N

  for i in range(N):
    arr: list[int] = MUL(S[i*D], two_C, D) # D-wise SIMD MUL
    half_size = D // 2 # we don't want floating division because SIMD instructions may not support them
    two_a_b_even: list[int] = [0] * half_size
    two_a_b_odd: list[int] = [0] * half_size

    while(half_size > 0):
      two_a_b_even, two_a_b_odd = SPLIT(arr, 2i, 2i+1) # I don't know what 2i and 2i+1 are, am copying it from slides
      arr = ADD(two_a_b_even, two_a_b_odd, half_size)
      half_size = half_size // 2

    two_a_b[i] = arr[0] # arr[0] should contain the sum


  C_sqr_sum_duplicated = [C_sqr_sum] * N # duplicate it so that we can use SIMD
  a_sqr_plus_b_sqr: list[int] = ADD(S_sqr_sum, C_sqr_sum_duplicated, N) # N-wise SIMD ADD
  differences: list[int] = SUB(a_sqr_plus_b_sqr, two_a_b, N) # N-wise SIMD SUB


  min_diff: int = differences[0]
  min_index: int = 0

  for k in range(N):
    if(differences[k] < min_diff):
      min_diff = differences[k]
      min_index = k

    return (min_diff, min_index)
