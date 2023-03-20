"""
The compiler does not import this file.
Instead, the MP-SPDZ program imports it,
and it provides some functions common to all generated MP-SPDZ programs
"""

import typing
import itertools

from Compiler.types import Array, Matrix, MultiArray, sint


TensorType = typing.Union[Array, Matrix, MultiArray]


T = typing.TypeVar("T")


def assign_tensor(tensor: TensorType, index: tuple[int], value: sint) -> None:
    if isinstance(tensor, Array):
        assert len(index) == 1
        tensor[index[0]] = value
    else:
        tensor.assign_vector_by_indices(value, *index)


def lift(
    expr: typing.Callable[[tuple[int, ...]], sint], dim_sizes: list[int]
) -> TensorType:
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
        assign_tensor(a, index, expr(index))
    return a


def drop_dim(arr: MultiArray) -> typing.Union[sint, TensorType]:
    """
    Drops the last dimension from @p arr, retaining the last element of each
      slice of that dimension.

    :param arr        The array to drop the last dimension from.

    :returns A copy of @p arr with the last dimension dropped.
    """

    dropped_shape = arr.shape[:-1]
    dropped_dim_size = arr.shape[-1]
    if len(dropped_shape) == 0:
        return arr[0]
    else:
        dropped = sint.Tensor(dropped_shape)

        all_indices = [range(size) for size in dropped_shape]
        for index in itertools.product(*all_indices):
            assign_tensor(
                dropped,
                index,
                arr.get_vector_by_indices(*index + (dropped_dim_size - 1,)),
            )

        return dropped
