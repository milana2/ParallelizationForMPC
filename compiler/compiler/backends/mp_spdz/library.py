"""
The compiler does not import this file.
Instead, the MP-SPDZ program imports it,
and it provides some functions common to all generated MP-SPDZ programs
"""

import typing
import math


T = typing.TypeVar("T")


def get_dim_indices(dim_sizes: list[int], index: int) -> list[int]:
    """Compute the per-dimension index"""

    dim_idxs = []
    for dim_size in dim_sizes:
        dim_idxs.append(index % dim_size)
        index //= dim_size
    return dim_idxs


def lift(expr: typing.Callable[[list[int]], T], dim_sizes: list[int]) -> list[T]:
    """
    Maps @p expr to an array specified by the provided dimensions.

    @param expr       The expression which will be evaluated at every position of the generated
    array.
    @param dim_sizes  The size of each dimension in the output array.

    @returns The lifted array.
    """

    return [
        expr(get_dim_indices(dim_sizes, index)) for index in range(math.prod(dim_sizes))
    ]


def drop_dim(arr: list[T], dim_sizes: list[int]) -> list[T]:
    """
    Drops the last dimension from @p arr, retaining the last element of each
      slice of that dimension.

    :param arr        The array to drop the last dimension from.
    :param dim_sizes  The size of each dimension in @p arr.

    :returns A copy of @p arr with the last dimension dropped.
    """

    dropped_size = len(arr) // dim_sizes[-1]
    dropped = []

    for i in range(dropped_size):
        in_idx = i
        for dim_size in dim_sizes[:-1]:
            in_idx *= dim_size
        in_idx += dim_sizes[-1] - 1
        dropped.append(arr[in_idx])

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
