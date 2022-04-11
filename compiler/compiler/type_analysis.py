from copy import copy
import dataclasses as dc
from typing import Optional, Union, cast

from .util import assert_never, replace_pattern

from . import loop_linear_code
from .dep_graph import DepGraph, DepNode, DepParameter
from .ast_shared import (
    Var,
    Constant,
    Subscript,
    BinOp,
    BinOpKind,
    UnaryOp,
    VarType,
    SubscriptIndex,
    SubscriptIndexBinOp,
    SubscriptIndexUnaryOp,
    VarVisibility,
    PLAINTEXT_INT,
    DataType,
    TypeEnv,
    VectorizedAccess,
)
from .tac_cfg import (
    AssignRHS,
    List,
    Tuple,
    Mux,
    Update,
    VectorizedUpdate,
    LiftExpr,
    DropDim,
)


def collect_idx_vars(idx: SubscriptIndex) -> list[Union[Var, Constant]]:
    if isinstance(idx, (Var, Constant)):
        return [idx]
    elif isinstance(idx, SubscriptIndexBinOp):
        if idx.operator == BinOpKind.ADD:
            return collect_idx_vars(idx.left) + collect_idx_vars(idx.right)
        elif idx.operator == BinOpKind.MUL:
            return collect_idx_vars(idx.left)
        else:
            raise SyntaxError(
                f"Unsupported binary operator '{idx.operator}' in subscript index.  Allowed operators are '+' and '*'"
            )
    elif isinstance(idx, SubscriptIndexUnaryOp):
        return collect_idx_vars(idx.operand)
    else:
        assert_never(idx)


def type_assign_expr(
    expr: Union[AssignRHS, SubscriptIndex, VectorizedAccess],
    type_env: TypeEnv,
    source_stmt: Optional[loop_linear_code.Statement],
    dep_graph: Optional[DepGraph],
) -> VarType:
    """
    Determines the type of an expression in a given type environment.  If an expression
    cannot be typed, this function returns None.
    """

    # TODO: switch all type errors to syntax errors with the locations of the offending
    # code in the original source code

    if isinstance(expr, Var):
        return type_env.get(expr, VarType())

    elif isinstance(expr, Constant):
        return VarType(VarVisibility.PLAINTEXT, 0, expr.datatype)

    elif isinstance(expr, Subscript):
        index_type = type_assign_expr(expr.index, type_env, source_stmt, dep_graph)
        if not index_type.could_become(PLAINTEXT_INT):
            raise TypeError(
                f"Array subscript index {expr.index} is not a plaintext int"
            )

        arr_type = type_env.get(expr.array, VarType())
        if arr_type is None:
            return VarType()

        if arr_type.datatype == DataType.TUPLE:
            raise TypeError(f"Tuples cannot be indexed into")

        return type_env[expr.array].drop_dim()

    elif isinstance(expr, BinOp):
        lhs_type = type_assign_expr(expr.left, type_env, source_stmt, dep_graph)
        rhs_type = type_assign_expr(expr.right, type_env, source_stmt, dep_graph)

        expr_type = VarType.merge(lhs_type, rhs_type)

        # Check that the operand types are valid for this operator.  The merge operation
        # validates that the two operands are compatible, so we just need to check their
        # merged type
        valid_operand_types = [*expr.operator.get_operand_datatypes(), None]
        if expr_type.datatype not in valid_operand_types:
            raise TypeError(
                f"Cannot perform {expr.operator} on {lhs_type.datatype} and {rhs_type.datatype}"
            )

        operator_datatype = expr.operator.get_ret_datatype()
        if operator_datatype is not None:
            expr_type.datatype = operator_datatype

        return expr_type

    elif isinstance(expr, UnaryOp):
        op_datatype = expr.operator.get_ret_datatype()
        expr_type = type_assign_expr(expr.operand, type_env, source_stmt, dep_graph)

        if expr_type.datatype not in [*expr.operator.get_operand_datatypes(), None]:
            raise TypeError(
                f"Operand of unary operator {expr.operator} is not of a valid type: found type '{expr_type}' but expected type in '{expr.operator.get_operand_datatypes()}'"
            )

        expr_type.datatype = op_datatype

        return expr_type

    elif isinstance(expr, List):
        if len(expr.items) == 0:
            # Edge case for initialization of empty lists/tuples
            # We assume that all arrays in the source-code are 1-dimensional
            # TODO: remove this condition if multi-dimensional arrays are supported
            # TODO: is it ok to assume that all hard-coded arrays are of ints?
            return VarType(VarVisibility.PLAINTEXT, 1, DataType.INT)

        elem_type = VarType.merge(
            *[
                type_assign_expr(item, type_env, source_stmt, dep_graph)
                for item in expr.items
            ],
            mixed_shared_plaintext_allowed=True,
        )

        return elem_type.add_dim()

    elif isinstance(expr, Tuple):
        elem_types = [
            type_assign_expr(item, type_env, source_stmt, dep_graph)
            for item in expr.items
        ]
        return VarType(
            VarVisibility.PLAINTEXT,  # Tuples are always plaintext
            1,  # tuples are always 1-dimensional
            DataType.TUPLE,
            tuple_types=elem_types,
        )

    elif isinstance(expr, Mux):
        _cond_type = type_assign_expr(expr.condition, type_env, source_stmt, dep_graph)

        true_type = type_assign_expr(expr.true_value, type_env, source_stmt, dep_graph)
        false_type = type_assign_expr(
            expr.false_value, type_env, source_stmt, dep_graph
        )

        expr_type = VarType.merge(
            true_type,
            false_type,
            mixed_shared_plaintext_allowed=True,
        )
        expr_type.visibility = VarVisibility.SHARED

        return expr_type

    elif isinstance(expr, Update):
        val_type = type_assign_expr(expr.value, type_env, source_stmt, dep_graph)
        arr_type = type_env.get(expr.array, VarType())
        index_type = type_assign_expr(expr.index, type_env, source_stmt, dep_graph)

        if arr_type.datatype == DataType.TUPLE:
            raise TypeError("Tuples cannot be updated")

        if not index_type.could_become(PLAINTEXT_INT):
            raise TypeError(
                f"Array subscript index {expr.index} is not a plaintext int"
            )

        # Erase the _dims value from the val_type to prevent conflict (_dims is manually overridden later)
        val_type_no_dims = dc.replace(val_type, _dims=None, dim_sizes=None)
        merged_type = VarType.merge(arr_type, val_type_no_dims)

        idx_vars = collect_idx_vars(expr.index)
        if not all(isinstance(var, Var) for var in idx_vars):
            raise SyntaxError(f"Array {expr.array} is indexed by a constant")

        idx_var_to_dim_size = {}
        assert source_stmt is not None
        assert dep_graph is not None
        for loop in dep_graph.enclosing_loops[source_stmt]:
            idx_var_to_dim_size[loop.counter] = loop.bound_high

        dim_sizes = [
            idx_var_to_dim_size[idx_var]
            for idx_var in idx_vars
            if isinstance(
                idx_var, Var
            )  # this is always true (checked above) but mypy doesn't know that
        ]

        return dc.replace(merged_type, _dims=len(idx_vars), dim_sizes=dim_sizes)

    elif isinstance(expr, VectorizedUpdate):
        val_type = type_assign_expr(expr.value, type_env, source_stmt, dep_graph)
        arr_type = type_env.get(expr.array, VarType())
        index_types = [
            type_assign_expr(idx_var, type_env, source_stmt, dep_graph)
            for idx_var in expr.idx_vars
        ]

        if arr_type.datatype == DataType.TUPLE:
            raise TypeError("Tuples cannot be updated")

        if not all(
            index_type.could_become(PLAINTEXT_INT) for index_type in index_types
        ):
            raise TypeError(
                f"Array subscript indices {expr.idx_vars} are not plaintext ints"
            )

        return VarType.merge(val_type, arr_type)

    elif isinstance(expr, LiftExpr):
        augmented_env = copy(type_env)
        for var, _bound in expr.dims:
            augmented_env[var] = PLAINTEXT_INT

        expr_type = type_assign_expr(expr.expr, augmented_env, source_stmt, dep_graph)

        return dc.replace(
            expr_type,
            _dims=0,
            dim_sizes=[loop_bound for _idx_var, loop_bound in expr.dims],
        )

    elif isinstance(expr, DropDim):
        expr_type = type_assign_expr(expr.array, type_env, source_stmt, dep_graph)
        return expr_type.drop_dim()

    elif isinstance(expr, VectorizedAccess):
        arr_type = type_env.get(expr.array, VarType())
        dim_sizes = [
            dim_size
            for dim_size, vectorized in zip(expr.dim_sizes, expr.vectorized_dims)
            if vectorized
        ]
        return dc.replace(
            arr_type,
            _dims=0,
            dim_sizes=dim_sizes if dim_sizes else None,
        )

    else:
        assert_never(expr)


def _add_loop_counter_types(
    type_env: TypeEnv, stmts: list[loop_linear_code.Statement]
) -> None:
    """
    Adds the types of the loop counters to the type environment.
    """
    for stmt in stmts:
        if isinstance(stmt, loop_linear_code.For):
            type_env[stmt.counter] = PLAINTEXT_INT
            _add_loop_counter_types(type_env, stmt.body)


def validate_type_requirements(
    stmts: list[loop_linear_code.Statement],
    type_env: TypeEnv,
    dep_graph: DepGraph,
    return_stmt: loop_linear_code.Statement,
    return_type: Optional[VarType],
) -> None:
    """
    Validates that all of MPC's type requirements are met and that all assignments/expressions
    have consistent dimensions.
    """
    for var_name, var_type in type_env.items():
        if not var_type.is_complete():
            raise TypeError(f"Variable {var_name} has incomplete type {var_type}")

        if var_type.datatype == DataType.TUPLE:
            if var_type.dims is not None and var_type.dims != 1:
                raise TypeError(
                    f"Tuple {var_name} has invalid dimensions {var_type.dims}"
                )
        else:
            if len(var_type.tuple_types) > 0:
                raise TypeError(
                    f"Variable {var_name} has tuple element types assigned, but it has datatype {var_type.datatype}"
                )

    for stmt in stmts:
        if isinstance(stmt, loop_linear_code.For):
            if type_env.get(stmt.counter) != PLAINTEXT_INT:
                raise TypeError(
                    f"Loop counter {stmt.counter.name} is not a plaintext integer"
                )
            validate_type_requirements(
                stmt.body, type_env, dep_graph, return_stmt, None
            )
        elif isinstance(stmt, loop_linear_code.Assign):
            # The type assignment function checks for type errors internally
            expr_type = type_assign_expr(stmt.rhs, type_env, stmt, dep_graph)
            if not expr_type.is_complete():
                raise TypeError(f"Unable to type expression {stmt.rhs}")

            if isinstance(stmt.lhs, VectorizedAccess):
                lhs_type = type_env.get(stmt.lhs.array)
                expr_type = dc.replace(expr_type, dim_sizes=list(stmt.lhs.dim_sizes))
            else:
                lhs_type = type_env.get(stmt.lhs)

            if lhs_type != expr_type:
                raise TypeError(f"Type mismatch in assignment {stmt.lhs} = {stmt.rhs}")
        elif isinstance(stmt, loop_linear_code.Phi):
            elem_types = [
                type_assign_expr(elem, type_env, stmt, dep_graph)
                for elem in stmt.rhs_vars()
            ]
            phi_type = VarType.merge(
                *elem_types, mixed_shared_plaintext_allowed=True, use_max_dim_size=True
            )
            if not phi_type.is_complete():
                raise TypeError(f"Unable to type phi expression {stmt}")

            if isinstance(stmt.lhs, VectorizedAccess):
                lhs_type = type_env.get(stmt.lhs.array)
                phi_type = dc.replace(phi_type, dim_sizes=list(stmt.lhs.dim_sizes))
            else:
                lhs_type = type_env.get(stmt.lhs)

            if lhs_type != phi_type:
                raise TypeError(f"Type mismatch in phi {stmt.lhs} = {stmt.rhs_vars()}")

    if not isinstance(return_stmt, loop_linear_code.Return):
        raise TypeError(
            f"Final statement {return_stmt} in function is not a Return statement"
        )

    if return_type is not None and not type_env[return_stmt.value].is_equivalent_to(
        return_type
    ):
        raise TypeError(
            f"Return type {type_env[return_stmt.value]} does not match expected type {return_type}"
        )


def type_check(
    func: loop_linear_code.Function, dep_graph: DepGraph
) -> tuple[loop_linear_code.Function, TypeEnv]:
    """
    Perform taint analysis to detect which variables are plaintext and which are shared.
    """

    type_env = TypeEnv(
        VarType,
        {param.var: param.var_type for param in func.parameters},
    )
    _add_loop_counter_types(type_env, func.body)

    worklist: list[DepNode] = list(dep_graph.def_use_graph.nodes)

    while len(worklist) > 0:
        stmt = worklist.pop()
        updated_lhs = False

        if isinstance(stmt, loop_linear_code.Assign):
            try:
                expr_type = type_assign_expr(stmt.rhs, type_env, stmt, dep_graph)
            except (TypeError, AssertionError) as e:
                raise TypeError(
                    f"Unable to type statement {stmt}\nType environment is:\n{type_env}"
                ) from e

            if isinstance(stmt.lhs, Var):
                orig_var = stmt.lhs
                new_var_type = expr_type
            elif isinstance(stmt.lhs, VectorizedAccess):
                orig_var = stmt.lhs.array
                new_var_type = dc.replace(expr_type, dim_sizes=list(stmt.lhs.dim_sizes))
            else:
                assert_never(stmt.lhs)

            if new_var_type != type_env.get(orig_var):
                type_env[orig_var] = new_var_type
                updated_lhs = True

        elif isinstance(stmt, loop_linear_code.Phi):
            elem_types = [
                type_assign_expr(elem, type_env, stmt, dep_graph)
                for elem in stmt.rhs_vars()
            ]
            try:
                phi_type = VarType.merge(
                    *elem_types,
                    mixed_shared_plaintext_allowed=True,
                    use_max_dim_size=True,
                )
            except (TypeError, AssertionError) as e:
                raise TypeError(
                    f"Unable to type statement {stmt}\nType environment is:\n{type_env}"
                ) from e

            lhs_var = stmt.lhs
            if isinstance(lhs_var, VectorizedAccess):
                lhs_var = lhs_var.array

            if phi_type != type_env.get(lhs_var):
                type_env[lhs_var] = phi_type
                updated_lhs = True

        elif isinstance(
            stmt, (DepParameter, loop_linear_code.For, loop_linear_code.Return)
        ):
            continue
        else:
            assert_never(stmt)

        if updated_lhs:
            worklist.extend([edge[1] for edge in dep_graph.def_use_graph.edges(stmt)])

    # At this point, all variables should be typed with their datatype and dimensions
    # Additionally, all shared variables should be marked as such
    # However, some plaintext variables may not be marked as plaintext if they're part of
    # a cycle of plaintext values.  The below loop updates those cases.
    for var_type in type_env.values():
        if var_type.visibility is None:
            var_type.visibility = VarVisibility.PLAINTEXT

    validate_type_requirements(
        func.body, type_env, dep_graph, func.body[-1], func.return_type
    )

    return func, type_env
