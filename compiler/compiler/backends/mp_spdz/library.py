"""
The compiler does not import this file.
Instead, the MP-SPDZ program imports it,
and it provides some functions common to all generated MP-SPDZ programs
"""

import typing
import itertools

from Compiler.library import print_str
from Compiler.types import Array, Matrix, MultiArray, sint


TensorType = typing.Union[Array, Matrix, MultiArray]

RevealableType = typing.Union[
    sint, list["RevealableType"], tuple["RevealableType", ...]
]

RevealedType = typing.Union[int, list["RevealedType"], tuple["RevealedType", ...]]

T = typing.TypeVar("T")


def assign_tensor(tensor: TensorType, index: tuple[int], value: sint) -> None:
    if isinstance(tensor, Array):
        assert len(index) == 1
        tensor[index[0]] = value
    else:
        tensor.assign_vector_by_indices(value, *index)


def lift(
    expr: typing.Union[
        typing.Callable[[tuple[int, ...]], typing.Union[int, sint]],
        typing.Callable[[tuple[int, ...]], Array],
    ],
    dim_sizes: list[int],
) -> TensorType:
    """
    Maps @p expr to an array specified by the provided dimensions.

    @param expr       The expression which will be evaluated at every position of the generated
    array.
    @param dim_sizes  The size of each dimension in the output array.

    @returns The lifted array.
    """

    zero_index = tuple(0 for _ in dim_sizes)
    first_value = expr(zero_index)
    if isinstance(first_value, (int, sint)):
        a = sint.Tensor(dim_sizes)
        all_indices = [range(size) for size in dim_sizes]
        for index in itertools.product(*all_indices):
            value = sint(expr(index))
            assign_tensor(a, index, value)
        return a
    else:
        assert isinstance(first_value, Array), type(first_value)
        source_array = first_value
        assert dim_sizes[0] <= len(source_array)
        lifted_array = sint.Tensor(dim_sizes)
        all_indices = [range(size) for size in dim_sizes]
        for index in itertools.product(*all_indices):
            assign_tensor(lifted_array, index, source_array[index[-1]])
        return lifted_array


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
        return arr[-1]
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


def mpc_print_result(x: RevealableType) -> None:
    def rec(x: RevealableType) -> None:
        if isinstance(x, (sint, Array, Matrix)):
            print_str("%s", x.reveal())
        elif isinstance(x, list):
            print_str("[")
            for i, item in enumerate(x):
                if i != 0:
                    print_str(", ")
                rec(item)
            print_str("]")
        elif isinstance(x, tuple):
            print_str("(")
            for i, item in enumerate(x):
                if i != 0:
                    print_str(", ")
                rec(item)
            print_str(")")
        else:
            raise ValueError(f"Tried to print unknown type {type(x)}")

    print_str("MPC BENCHMARK OUTPUT ")
    rec(x)
    print_str("\n")
