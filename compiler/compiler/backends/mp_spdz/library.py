"""
The compiler does not import this file.
Instead, the MP-SPDZ program imports it,
and it provides some functions common to all generated MP-SPDZ programs
"""

import typing
import math
import itertools


T = typing.TypeVar("T")


def get_dim_indices(dim_sizes: list[int], index: int) -> list[int]:
    """Compute the per-dimension index"""

    dim_idxs = []
    for dim_size in dim_sizes:
        dim_idxs.append(index % dim_size)
        index //= dim_size
    return dim_idxs


def lift(expr: typing.Callable[[list[int]], T], dim_sizes: list[int]) -> MultiArray:
    """
    Maps @p expr to an array specified by the provided dimensions.

    @param expr       The expression which will be evaluated at every position of the generated
    array.
    @param dim_sizes  The size of each dimension in the output array.

    @returns The lifted array.
    """

    a = MultiArray(dim_sizes, sint)
    all_indices = [range(size) for size in dim_sizes]
    for index in itertools.product(*all_indices):
        a.get(index) = expr(index)
    return a


def drop_dim(arr: MultiArray) -> MultiArray:
    """
    Drops the last dimension from @p arr, retaining the last element of each
      slice of that dimension.

    :param arr        The array to drop the last dimension from.

    :returns A copy of @p arr with the last dimension dropped.
    """

    dropped_shape = arr.shape[:-1]
    dropped = MultiArray(dropped_shape, sint)

    all_indices = [range(size) for size in dropped_shape]
    for index in itertools.product(*all_indices):
        dropped.get(index) = arr.get(list(index) + [-1])

    return dropped


# Compute the slice of an array.
def vectorized_access(
    arr: list[T], dim_sizes: list[int], vectorized_dims: list[bool], idxs: list[int]
) -> list[T]:
    bucket = []

    # Collect the elements of the selected slice.
    for i in range(len(arr)):
        dim_idxs = get_dim_indices(dim_sizes, i)

        # Check that the indices match for all non-vectorized dimensions.
        match = True
        which_idx = 0
        for k in range(len(dim_idxs)):
            if vectorized_dims[k]:
                continue
            else:
                if dim_idxs[k] != idxs[which_idx]:
                    match = False
                    break
                which_idx += 1
        if match:
            bucket.append(arr[i])

    return bucket


# Compute the slice of an array.
def vectorized_assign(
    target: list[T],
    dim_sizes: list[int],
    vectorized_dims: list[bool],
    idxs: list[int],
    unvectorized_source: list[T],
) -> None:
    # For each element in the unvectorized representation, find the corresponding index in the
    # target array and assign the value.
    for i, source_value in enumerate(unvectorized_source):
        target_dim_idxs = get_dim_indices(dim_sizes, i)
