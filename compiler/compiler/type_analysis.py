import sys
from typing import Optional, Union, cast

from . import loop_linear_code
from .dep_graph import DepGraph
from .ast_shared import (
    Var,
    Constant,
    Subscript,
    BinOp,
    UnaryOp,
    VarType,
    SubscriptIndex,
    VarVisibility,
    PLAINTEXT_INT,
    DataType,
    TypeEnv,
)
from .tac_cfg import AssignRHS, List, Tuple, Mux, Update


def _type_assign_expr(
    expr: Union[AssignRHS, SubscriptIndex], type_env: TypeEnv
) -> VarType:
    """
    Determines the type of an expression in a given type environment.  If an expression
    cannot be typed, this function returns None.
    """

    # TODO: switch all type errors to syntax errors with the locations of the offending
    # code in the original source code

    if isinstance(expr, Var):
        return type_env[expr]

    elif isinstance(expr, Constant):
        return VarType(VarVisibility.PLAINTEXT, 0, expr.datatype)

    elif isinstance(expr, Subscript):
        index_type = _type_assign_expr(expr.index, type_env)
        if not index_type.could_become(PLAINTEXT_INT):
            raise TypeError(
                f"Array subscript index {expr.index} is not a plaintext int"
            )

        arr_type = type_env[expr.array]
        if arr_type.datatype == DataType.TUPLE:
            raise TypeError(f"Tuples cannot be indexed into")

        return type_env[expr.array].drop_dim()

    elif isinstance(expr, BinOp):
        lhs_type = _type_assign_expr(expr.left, type_env)
        rhs_type = _type_assign_expr(expr.right, type_env)

        expr_type = VarType.merge(lhs_type, rhs_type)

        # Check that the operand types are valid for this operator.  The merge operation
        # validates that the two operands are compatible, so we just need to check their
        # merged type
        valid_operand_types = [*expr.operator.get_operand_datatypes(), None]
        if expr_type.datatype not in valid_operand_types:
            raise TypeError(
                f"Cannot perform {expr.operator} on {lhs_type.datatype} and {rhs_type.datatype}"
            )

        expr_type.datatype = expr.operator.get_ret_datatype()

        return expr_type

    elif isinstance(expr, UnaryOp):
        op_datatype = expr.operator.get_ret_datatype()
        expr_type = _type_assign_expr(expr.operand, type_env)

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
            *[_type_assign_expr(item, type_env) for item in expr.items],
            mixed_shared_plaintext_allowed=True,
        )

        return elem_type.add_dim()

    elif isinstance(expr, Tuple):
        elem_types = [_type_assign_expr(item, type_env) for item in expr.items]
        return VarType(
            VarVisibility.PLAINTEXT,  # Tuples are always plaintext
            1,  # tuples are always 1-dimensional
            DataType.TUPLE,
            tuple_types=elem_types,
        )

    elif isinstance(expr, Mux):
        cond_type = _type_assign_expr(expr.condition, type_env)
        if cond_type.is_plaintext():
            raise AssertionError(
                f"Condition {expr.condition} of Mux expression {expr} is not a shared variable."
            )

        true_type = _type_assign_expr(expr.true_value, type_env)
        false_type = _type_assign_expr(expr.false_value, type_env)

        expr_type = VarType.merge(
            true_type,
            false_type,
            mixed_shared_plaintext_allowed=True,
        )
        expr_type.visibility = VarVisibility.SHARED

        # Validate the dimensions
        if (
            cond_type.dims is not None
            and expr_type.dims is not None
            and cond_type.dims > expr_type.dims
        ):
            raise TypeError(
                "The true/false values of a MUX must have the same or fewer dimensions than the condition"
            )

        return expr_type

    elif isinstance(expr, Update):
        val_type = _type_assign_expr(expr.value, type_env)
        arr_type = type_env[expr.array]
        index_type = _type_assign_expr(expr.index, type_env)

        if arr_type.datatype == DataType.TUPLE:
            raise TypeError(f"Tuples cannot be updated")

        if not index_type.could_become(PLAINTEXT_INT):
            raise TypeError(
                f"Array subscript index {expr.index} is not a plaintext int"
            )

        val_arr_type = val_type.add_dim()
        return VarType.merge(val_arr_type, arr_type)

    raise AssertionError(f"Unexpected type {type(expr)} passed to _type_assign_expr")


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
    return_var: Var,
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
            if var_type.dims != 1:
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
            if type_env[stmt.counter] != PLAINTEXT_INT:
                raise TypeError(
                    f"Loop counter {stmt.counter.name} is not a plaintext integer"
                )
            validate_type_requirements(stmt.body, type_env, return_var, None)
        elif isinstance(stmt, loop_linear_code.Assign):
            # The type assignment function checks for type errors internally
            if not _type_assign_expr(stmt.rhs, type_env).is_complete():
                raise TypeError(f"Unable to type expression {stmt.rhs}")

            if type_env[stmt.lhs] != _type_assign_expr(stmt.rhs, type_env):
                raise TypeError(f"Type mismatch in assignment {stmt.lhs} = {stmt.rhs}")
        elif isinstance(stmt, loop_linear_code.Phi):
            elem_types = [_type_assign_expr(elem, type_env) for elem in stmt.rhs_vars()]
            phi_type = VarType.merge(*elem_types, mixed_shared_plaintext_allowed=True)
            if not phi_type.is_complete():
                raise TypeError(f"Unable to type phi expression {stmt}")

            if type_env[stmt.lhs] != phi_type:
                raise TypeError(f"Type mismatch in phi {stmt.lhs} = {stmt.rhs_vars()}")

    if return_type is not None and type_env[return_var] != return_type:
        from pprint import pprint

        pprint(type_env[return_var])
        pprint(return_type)

        raise TypeError(
            f"Return type {type_env[return_var]} does not match expected type {return_type}"
        )


def type_check(func: loop_linear_code.Function, dep_graph: DepGraph) -> TypeEnv:
    """
    Perform taint analysis to detect which variables are plaintext and which are shared.
    """

    type_env = TypeEnv(
        VarType,
        {
            # TODO: fix the below hack once parameter ssa renaming is properly implemented
            Var(param.var.name, 0): cast(VarType, param.var_type)
            for param in func.parameters
        },
    )
    _add_loop_counter_types(type_env, func.body)

    worklist = list(dep_graph.def_use_graph.nodes)

    while len(worklist) > 0:
        stmt = worklist.pop()
        if isinstance(stmt, loop_linear_code.Assign):
            try:
                expr_type = _type_assign_expr(stmt.rhs, type_env)
            except (TypeError, AssertionError) as e:
                raise TypeError(f"Unable to type statement {stmt}") from e

            if expr_type == type_env[stmt.lhs]:
                # No changes to this variable's type, don't extend the worklist
                continue
            type_env[stmt.lhs] = expr_type

        elif isinstance(stmt, loop_linear_code.Phi):
            elem_types = [_type_assign_expr(elem, type_env) for elem in stmt.rhs_vars()]
            try:
                phi_type = VarType.merge(
                    *elem_types,
                    mixed_shared_plaintext_allowed=True,
                )
            except (TypeError, AssertionError) as e:
                raise TypeError(f"Unable to type statement {stmt}") from e
            if phi_type == type_env[stmt.lhs]:
                # No changes to this variable's type, don't extend the worklist
                continue
            type_env[stmt.lhs] = phi_type
        else:
            raise AssertionError(
                f"Unexpected node {type(stmt)} added to type inference worklist"
            )

        # If we get to this point, the lhs has been reassigned so we must add dependencies
        # to the worklist
        worklist.extend([edge[1] for edge in dep_graph.def_use_graph.edges(stmt)])

    # At this point, all variables should be typed with their datatype and dimensions
    # Additionally, all shared variables should be marked as such
    # However, some plaintext variables may not be marked as plaintext if they're part of
    # a cycle of plaintext values.  The below loop updates those cases.
    for var_type in type_env.values():
        if var_type.visibility is None:
            var_type.visibility = VarVisibility.PLAINTEXT

    validate_type_requirements(func.body, type_env, func.return_value, func.return_type)

    return type_env
