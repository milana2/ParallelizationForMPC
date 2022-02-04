from typing import Callable


def raise_dim(
    arr: list[int], access_pattern: Callable[[list[int]], int], dim_sizes: list[int]
) -> list[int]:
    """
    Reshapes @p arr to the shape provided by @p dim_sizes.  @p access_pattern provides
      the mapping between the original and the reshaped array.

    :param arr             The array to reshape.
    :param access_pattern  Mapping of an index in the output array (broken down
    :                        by dimension) to an index in the input array.
    :param dim_sizes       The size of each dimension in the output array.

    :returns The reshaped array.
    """

    raised_size = 1
    for dim_size in dim_sizes:
        raised_size *= dim_size

    raised = [0] * raised_size

    for i in range(raised_size):
        dim_idxs = [0] * len(dim_sizes)
        for dim_idx, dim_size in enumerate(dim_sizes):
            dim_idxs[dim_idx] = i % dim_size
            i //= dim_size

        raised[i] = arr[access_pattern(dim_idxs)]

    return raised


def drop_dim(arr: list[int], dim_sizes: list[int]) -> list[int]:
    """
    Drops the last dimension from @p arr, retaining the last element of each
      slice of that dimension.

    :param arr        The array to drop the last dimension from.
    :param dim_sizes  The size of each dimension in @p arr.

    :returns A copy of @p arr with the last dimension dropped.
    """

    dropped_size = len(arr) // dim_sizes[-1]
    dropped = [0] * dropped_size

    for i in range(dropped_size):
        in_idx = i
        for dim_size in dim_sizes[:-1]:
            in_idx *= dim_size
        in_idx += dim_sizes[-1] - 1
        dropped[i] = arr[in_idx]

    return dropped
