"""
The compiler does not import this file.
Instead, the MP-SPDZ program imports it,
and it provides some functions common to all generated MP-SPDZ programs
"""

import typing
import itertools

from Compiler.types import Array, MultiArray, sint


T = typing.TypeVar("T")


def lift(
    expr: typing.Callable[[tuple[int, ...]], sint], dim_sizes: list[int]
) -> MultiArray:
    """
    Maps @p expr to an array specified by the provided dimensions.

    @param expr       The expression which will be evaluated at every position of the generated
    array.
    @param dim_sizes  The size of each dimension in the output array.

    @returns The lifted array.
    """

    a = sint.Tensor(dim_sizes)
    all_indices = [range(size) for size in dim_sizes]
    for index in itertools.product(*all_indices):
        if isinstance(a, Array):
            assert len(index) == 1
            a[index[0]] = expr(index)
        else:
            a.assign_vector_by_indices(expr(index), *index)
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
        dropped.assign_vector_by_indices(
            arr.get_vector_by_indices(list(index) + [-1]), *index
        )

    return dropped


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
