"""
The compiler does not import this file.
Instead, the MP-SPDZ program imports it,
and it provides some functions common to all generated MP-SPDZ programs
"""

import typing
import itertools


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
        return vector.elements()[index]
    except AttributeError:
        return vector[index]


class VectorizationLibrary:
    def __init__(self, globals):
        self._print_str = globals["print_str"]
        self._Array = globals["Array"]
        self._Matrix = globals["Matrix"]
        self._MultiArray = globals["MultiArray"]
        self._sint = globals["sint"]

        try:
            self.sbool = globals["sintbit"]
        except KeyError:
            self.sbool = globals["sbitintvec"].get_type(1)

    def vectorized_access(self, array, indices: tuple[typing.Optional[int]]):
        indices_full = _expand_vectorized_indices(array.shape, indices)
        result_array = self._Array(len(indices_full), array.value_type)
        for result_index, tensor_index in enumerate(indices_full):
            result_array[result_index] = self.access_tensor(array, tensor_index)
        return result_array.get_vector()

    def vectorized_assign(
        self, array, indices: tuple[typing.Optional[int]], value
    ) -> None:
        indices_full = _expand_vectorized_indices(array.shape, indices)
        assert len(indices_full) == value.size, (indices_full, value.size)
        for value_index, tensor_index in enumerate(indices_full):
            value_elem = _index_register_vector(value, value_index)
            self.assign_tensor(array, tensor_index, value_elem)

    def access_tensor(self, array, indices: typing.Union[tuple[int], list[int]]):
        a = array
        for index in indices:
            a = a[index]
        return a

    def assign_tensor(
        self, tensor, index: typing.Union[list[int], tuple[int]], value
    ) -> None:
        if isinstance(tensor, self._Array):
            assert len(index) == 1
            tensor[index[0]] = value
        else:
            t = tensor
            slices = [t]
            for dim_index in index[:-1]:
                t = t[dim_index]
                slices.append(t)
            t[index[-1]] = value

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
            a = value_type.Tensor(dim_sizes)
            all_indices = [range(size) for size in dim_sizes]
            for index in itertools.product(*all_indices):
                value = value_type(expr(index))
                self.assign_tensor(a, index, value)
            return a
        else:
            assert isinstance(first_value, self._Array) or (
                isinstance(first_value, (self._sint, self.sbool))
                and first_value.size > 1
            ), type(first_value)
            source_array = first_value
            source_array_len = (
                len(source_array)
                if isinstance(first_value, self._Array)
                else source_array.size
            )
            assert dim_sizes[0] <= source_array_len
            value_type = (
                first_value.value_type
                if isinstance(first_value, self._Array)
                else type(first_value)
            )
            lifted_array = value_type.Tensor(dim_sizes)
            all_indices = [range(size) for size in dim_sizes]
            for index in itertools.product(*all_indices):
                last_index = index[-1]
                source_array_elem = (
                    source_array[last_index]
                    if isinstance(source_array, self._Array)
                    else _index_register_vector(source_array, last_index)
                )
                self.assign_tensor(lifted_array, index, source_array_elem)
            return lifted_array

    def drop_dim(self, arr):
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
            dropped = arr.value_type.Tensor(dropped_shape)

            all_indices = [range(size) for size in dropped_shape]
            for index in itertools.product(*all_indices):
                self.assign_tensor(
                    dropped,
                    index,
                    self.access_tensor(arr, index + (dropped_dim_size - 1,)),
                )

            return dropped

    def mpc_print_result(self, x) -> None:
        def rec(x) -> None:
            if isinstance(x, (self._sint, self._Array, self._Matrix)):
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
