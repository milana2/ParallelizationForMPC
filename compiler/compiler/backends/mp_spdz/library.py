"""
The compiler does not import this file.
Instead, the MP-SPDZ program imports it,
and it provides some functions common to all generated MP-SPDZ programs
"""

import math
import typing
import itertools
import functools


def _expand_vectorized_indices(
    array_shape: list[int], indices: tuple[typing.Optional[int]]
) -> list[list[int]]:
    dim_idx_iters = [
        range(array_shape[dim]) if idx is None else [idx]
        for (dim, idx) in enumerate(indices)
    ]

    return list(itertools.product(*dim_idx_iters))


def _index_register_vector(vector, index):
    try:
        return type(vector)(vector.elements()[index])
    except AttributeError:
        return vector[index]


def _unsimdify(vector):
    if isinstance(vector, list):
        return vector
    elif vector.size == 1:
        return [vector]
    else:
        try:
            return [type(vector)(value) for value in vector.elements()]
        except AttributeError:
            return [vector[i] for i in range(vector.size)]


def _compute_flat_index(index: list[int], shape: list[int]) -> int:
    flat_index = 0
    for dim_index, dim_size in zip(index, shape):
        flat_index = flat_index * dim_size + dim_index
    return flat_index


class _SimdifyInput:
    """
    Wrapper class around lists of `sint`s

    This overloads `__hash__` and `__eq__` so that it can be used with
    `functools.cache` to cache the results of simdification.  The built-in
    `__eq__` on `sint` can't be used because it compiles a comparison
    instruction instead of checking whether the `sint`s are the same object.
    """

    def __init__(self, values: list) -> None:
        self.values = values

    def __hash__(self) -> int:
        return hash(tuple(id(value) for value in self.values))

    def __eq__(self, other) -> bool:
        return len(self.values) == len(other.values) and all(
            v is o for (v, o) in zip(self.values, other.values)
        )


class VectorizationLibrary:
    def __init__(self, globals):
        self._print_str = globals["print_str"]
        self._sint = globals["sint"]
        self._sbits = globals["sbits"]

        try:
            self.sbool = globals["sintbit"]
        except KeyError:
            self.sbool = globals["sbitintvec"].get_type(1)

    @functools.cache
    def _simdify(self, input: _SimdifyInput):
        values = input.values
        first = values[0]
        if len(values) == 1:
            return first
        element_type = self.sbool if isinstance(first, self.sbool) else self._sint
        try:
            return element_type(values)
        except:
            return element_type([self._sbits(value) for value in values])

    def vectorized_access(
        self, array: list, shape: list[int], indices: tuple[typing.Optional[int]]
    ):
        indices_full = _expand_vectorized_indices(shape, indices)
        result_list = []
        for tensor_index in indices_full:
            result_list.append(self.access_tensor(array, tensor_index, shape))
        return self._simdify(_SimdifyInput(result_list))

    def vectorized_assign(
        self, array, shape: list[int], indices: tuple[typing.Optional[int]], value
    ) -> None:
        assert value is not None
        indices_full = _expand_vectorized_indices(shape, indices)
        value = _unsimdify(value)
        assert len(indices_full) == len(value)
        for value_index, tensor_index in enumerate(indices_full):
            value_elem = value[value_index]
            self.assign_tensor(array, tensor_index, shape, value_elem)

    def access_tensor(
        self, array: list, index: typing.Union[tuple[int], list[int]], shape: list[int]
    ):
        flat_index = _compute_flat_index(index, shape)
        return array[flat_index]

    def assign_tensor(
        self,
        tensor,
        index: typing.Union[list[int], tuple[int]],
        shape: list[int],
        value,
    ) -> None:
        flat_index = _compute_flat_index(index, shape)
        tensor[flat_index] = value

    def lift(
        self, expr: typing.Callable[[tuple[int, ...]], typing.Any], dim_sizes: list[int]
    ):
        """
        Maps @p expr to an array specified by the provided dimensions.

        @param expr       The expression which will be evaluated at every position of the generated
        array.
        @param dim_sizes  The size of each dimension in the output array.

        @returns The lifted array.
        """

        zero_index = tuple(0 for _ in dim_sizes)
        first_value = expr(zero_index)
        if isinstance(first_value, int) or (
            isinstance(first_value, (self._sint, self.sbool)) and first_value.size == 1
        ):
            value_type = (
                self.sbool if isinstance(first_value, self.sbool) else self._sint
            )
            a = [None] * math.prod(dim_sizes)
            all_indices = [range(size) for size in dim_sizes]
            for index in itertools.product(*all_indices):
                value = value_type(expr(index))
                self.assign_tensor(a, index, dim_sizes, value)
            return a
        else:
            assert isinstance(first_value, list) or (
                isinstance(first_value, (self._sint, self.sbool))
                and first_value.size > 1
            ), type(first_value)
            source_array = first_value
            source_array_len = (
                len(source_array)
                if isinstance(first_value, list)
                else source_array.size
            )
            assert dim_sizes[0] <= source_array_len, source_array
            value_type = (
                type(first_value[0])
                if isinstance(first_value, list)
                else type(first_value)
            )
            lifted_array = [None] * math.prod(dim_sizes)
            all_indices = [range(size) for size in dim_sizes]
            for index in itertools.product(*all_indices):
                last_index = index[-1]
                source_array_elem = (
                    source_array[last_index]
                    if isinstance(source_array, list)
                    else _index_register_vector(source_array, last_index)
                )
                self.assign_tensor(lifted_array, index, dim_sizes, source_array_elem)
            return lifted_array

    def drop_dim(self, arr: list, shape: list[int]) -> list:
        """
        Drops the last dimension from @p arr, retaining the last element of each
        slice of that dimension.

        :param arr        The array to drop the last dimension from.

        :returns A copy of @p arr with the last dimension dropped.
        """

        dropped_shape = shape[:-1]
        dropped_dim_size = shape[-1]
        if len(dropped_shape) == 0:
            return arr[-1]
        else:
            dropped = [None] * math.prod(dropped_shape)

            all_indices = [range(size) for size in dropped_shape]
            for index in itertools.product(*all_indices):
                self.assign_tensor(
                    dropped,
                    index,
                    dropped_shape,
                    self.access_tensor(arr, index + (dropped_dim_size - 1,), shape),
                )

            return dropped

    def mpc_print_result(self, x) -> None:
        def rec(x) -> None:
            if hasattr(x, "reveal"):
                assert not isinstance(x, (list, tuple))
                self._print_str("%s", x.reveal())
            elif isinstance(x, list):
                self._print_str("[")
                for i, item in enumerate(x):
                    if i != 0:
                        self._print_str(", ")
                    rec(item)
                self._print_str("]")
            elif isinstance(x, tuple):
                self._print_str("(")
                for i, item in enumerate(x):
                    if i != 0:
                        self._print_str(", ")
                    rec(item)
                self._print_str(")")
            else:
                raise ValueError(f"Tried to print unknown type {type(x)}")

        self._print_str("MPC BENCHMARK OUTPUT ")
        rec(x)
        self._print_str("\n")
