def raise_dim(
    arr: list[int], dims_in_arr: list[int], all_dims: list[int], dim_to_raise: int
) -> list[int]:
    """
    NOTE: This implementation is a recreation of the C++ implementation, so it could probably
    be made more pythonic.

    Raises the dimensionality of `arr` by extending it over dimension `dim_to_raise`.
    Example: raise_dim([0, 1, 2], [0], [3, 2], 1) will return [0, 0, 1, 1, 2, 2]
    Example: raise_dim([0, 1, 2], [1], [2, 3], 0) will return [0, 1, 2, 0, 1, 2]

    :param arr           Input array.  This array's elements should be ordered in row-major
                           order according to `dims_in_arr`.
    :param dims_in_arr   Order sequence of which dimensions are in `arr`.  Each number in
                           this array refers to an index in `all_dims` corresponding to
                           the relevant dimension. THIS ARRAY MUST BE SORTED IN ASCENDING
                           ORDER.
    :param all_dims      Array sizes of each dimsnion.  For example, the array [2, 1, 3]
                           means that dimension 0 has size 2, dimension 1 has size 1, and
                           dimension 2 has size 3.
    :param dim_to_raise  Index of the dimension `all_dims` to extend `arr` over.  This index
                           cannot be in `dims_in_arr`.

    :returns The extended version of `arr`
    """
    raised_size = all_dims[dim_to_raise]
    for dim_idx in dims_in_arr:
        assert dim_idx != dim_to_raise
        raised_size *= all_dims[dim_idx]

    raised = [0] * raised_size

    dims_in_raised = sorted([*dims_in_arr, dim_to_raise])

    def RaisedArrIdx(idx_in_arr: int, idx_in_dim: int) -> int:
        dim_idxs = [0] * len(dims_in_arr)
        for dim_idx in reversed(range(len(dims_in_arr))):
            dim_size = all_dims[dims_in_arr[dim_idx]]

            dim_idxs[dim_idx] = idx_in_arr % dim_size
            # Drop the most recent dimension from the array index
            idx_in_arr //= dim_size

        raised_idx = 0
        dim_idx = 0
        # Go over dimensions until we reach the one we're raising over
        while (
            dim_idx < len(dims_in_arr)
            and dims_in_arr[dim_idx] == dims_in_raised[dim_idx]
        ):
            raised_idx *= all_dims[dims_in_arr[dim_idx]]
            raised_idx += dim_idxs[dim_idx]
            dim_idx += 1

        # We've reached the dimension which we're adding to the array
        raised_idx *= all_dims[dim_to_raise]
        raised_idx += idx_in_dim

        # Go through the rest of the dimensions
        while dim_idx < len(dims_in_arr):
            raised_idx *= all_dims[dims_in_arr[dim_idx]]
            raised_idx += dim_idxs[dim_idx]
            dim_idx += 1

        return raised_idx

    for dim_idx in range(all_dims[dim_to_raise]):
        for arr_idx in range(len(arr)):
            raised[RaisedArrIdx(arr_idx, dim_idx)] = arr[arr_idx]

    return raised


def drop_dim(
    arr: list[int], dims_in_arr: list[int], all_dims: list[int], dim_to_drop: int
) -> list[int]:
    dropped = [0] * (len(arr) // all_dims[dim_to_drop])

    # Compute the number of elements corresponding to a single slice of this dimension
    slice_size = 1
    for dim_idx in reversed(dims_in_arr):
        if dim_idx == dim_to_drop:
            break
        slice_size *= all_dims[dim_idx]

    # skip_size holds how many elements we should skip over (e.g. the intermediate values)
    skip_size = slice_size * (all_dims[dim_to_drop] - 1)

    out_idx = 0
    arr_idx = skip_size
    while arr_idx < len(arr):
        for _ in range(slice_size):
            dropped[out_idx] = arr[arr_idx]
            out_idx += 1
            arr_idx += 1
        # arr_idx is now pointing at the beginning of the dropped dimension's next row
        arr_idx += skip_size

    return dropped
