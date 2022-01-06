import sys
from typing import Optional, Union, cast

from . import loop_linear_code
from .dep_graph import DepGraph
from .ast_shared import (
    Var,
    ConstantInt,
    Subscript,
    BinOp,
    UnaryOp,
    VarType,
    SubscriptIndex,
    VarVisibility,
    PLAINTEXT_INT,
)
from .tac_cfg import AssignRHS, List, Tuple, Mux, Update


class TypeEnv(dict[Var, VarType]):
    def __str__(self) -> str:
        return "\n".join([f"{var}: {var_type}" for var, var_type in self.items()])


def _type_assign_expr(
    expr: Union[AssignRHS, SubscriptIndex], type_env: TypeEnv
) -> Optional[VarType]:
    """
    Determines the type of an expression in a given type environment.  If an expression
    cannot be typed, this function returns None.
    """

    # TODO: switch all type errors to syntax errors with the locations of the offending
    # code in the original source code

    if isinstance(expr, Var):
        return type_env.get(expr)

    elif isinstance(expr, ConstantInt):
        return PLAINTEXT_INT

    elif isinstance(expr, Subscript):
        if _type_assign_expr(expr.index, type_env) != PLAINTEXT_INT:
            raise TypeError(
                f"Array subscript index {expr.index} is not a plaintext int"
            )
        arr_type = type_env.get(expr.array)
        if arr_type is not None:
            return arr_type.drop_dim()
        else:
            return None

    elif isinstance(expr, BinOp):
        lhs_type = _type_assign_expr(expr.left, type_env)
        rhs_type = _type_assign_expr(expr.right, type_env)

        if lhs_type is not None and rhs_type is not None:
            if lhs_type.dims != rhs_type.dims:
                raise TypeError("Cannot add arrays of different dimensions")

            if lhs_type.is_plaintext() and rhs_type.is_plaintext():
                return VarType(VarVisibility.PLAINTEXT, lhs_type.dims)
            else:
                return VarType(VarVisibility.SHARED, lhs_type.dims)
        elif lhs_type is not None and lhs_type.is_shared():
            return lhs_type
        elif rhs_type is not None and rhs_type.is_shared():
            return rhs_type
        else:
            return None

    elif isinstance(expr, UnaryOp):
        return _type_assign_expr(expr.operand, type_env)

    elif isinstance(expr, (List, Tuple)):
        if len(expr.items) == 0:
            # Edge case for initialization of empty lists/tuples
            # We assume that all arrays in the source-code are 1-dimensional
            # TODO: remove this condition if multi-dimensional arrays are supported
            return VarType(VarVisibility.PLAINTEXT, 1)

        elem_types = [_type_assign_expr(elem, type_env) for elem in expr.items]
        elem_dims = [
            elem_type.dims for elem_type in elem_types if elem_type is not None
        ]

        if len(elem_dims) == 0:
            return None  # we can't type any of the elements of the container yet
        elif not all(elem_dims[0] == elem_dim for elem_dim in elem_dims):
            raise TypeError("All elements of a container must have the same dimensions")

        if all(
            elem_type is not None and elem_type.is_plaintext()
            for elem_type in elem_types
        ):
            assert elem_types[0] is not None  # needed for mypy
            return elem_types[0].add_dim()
        else:
            for elem_type in elem_types:
                if elem_type is not None and elem_type.is_shared():
                    return elem_type.add_dim()

    elif isinstance(expr, Mux):
        cond_type = _type_assign_expr(expr.condition, type_env)
        if cond_type is not None and cond_type.is_plaintext():
            print(
                f"[WARNING]: MUX condition `{expr.condition}` is plaintext",
                file=sys.stderr,
            )

        true_type = _type_assign_expr(expr.true_value, type_env)
        false_type = _type_assign_expr(expr.false_value, type_env)

        if true_type is None and false_type is None:
            # We can't determine the dimensions of the returned value yet
            return None

        if (
            true_type is not None
            and false_type is not None
            and true_type.dims != false_type.dims
        ):
            raise TypeError(
                "True and false values of a MUX must have the same dimensions"
            )

        if cond_type is not None and (
            (true_type is not None and cond_type.dims > true_type.dims)
            or (false_type is not None and cond_type.dims > false_type.dims)
        ):
            raise TypeError(
                "The true/false values of a MUX must have the same or fewer dimensions than the condition"
            )

        if true_type is not None:
            ret_dims = true_type.dims
        else:
            # the below assertion is not necessary due to the above check, but my
            # typechecker complains when it's missing
            assert false_type is not None
            ret_dims = false_type.dims

        return VarType(VarVisibility.SHARED, ret_dims)

    elif isinstance(expr, Update):
        val_type = _type_assign_expr(expr.value, type_env)
        arr_type = type_env.get(expr.array)

        if val_type is not None and arr_type is not None:
            if val_type.dims != arr_type.dims - 1:
                raise TypeError(
                    "Cannot update array with value of different dimensions than its element type"
                )

            if val_type.is_shared():
                return VarType(VarVisibility.SHARED, arr_type.dims)
            else:
                return arr_type
        elif arr_type is not None and arr_type.is_shared():
            return arr_type
        elif val_type is not None and val_type.is_shared():
            return val_type.add_dim()
        else:
            return None

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
    stmts: list[loop_linear_code.Statement], type_env: TypeEnv
) -> None:
    """
    Validates that all of MPC's type requirements are met and that all assignments/expressions
    have consistent dimensions.
    """
    for var_name, var_type in type_env.items():
        if var_type.dims < 0:
            raise TypeError(f"Variable {var_name} has negative dimensions")

    for stmt in stmts:
        if isinstance(stmt, loop_linear_code.For):
            if type_env[stmt.counter] != PLAINTEXT_INT:
                raise TypeError(f"Loop counter {stmt.counter.name} is not plaintext")
            validate_type_requirements(stmt.body, type_env)
        elif isinstance(stmt, loop_linear_code.Assign):
            # The type assignment function checks for type errors internally
            if _type_assign_expr(stmt.rhs, type_env) is None:
                # TODO: I think that this case being hit means that the type of the LHS variable
                #   is plaintext, but due to having a def-use cycle of plaintext values the
                #   primary algorithm doesn't detect this case.
                pass
        elif isinstance(stmt, loop_linear_code.Phi):
            elem_types = [_type_assign_expr(elem, type_env) for elem in stmt.rhs]

            if any(elem_type is None for elem_type in elem_types):
                # TODO: as above, this case can be triggered by a def-use cycle of plaintext values
                # raise TypeError(f"Cannot determine type of one or more elements of Phi node {stmt}")
                pass

            elem_dims = [
                elem_type.dims for elem_type in elem_types if elem_type is not None
            ]
            if len(set(elem_dims)) > 1:
                raise TypeError(
                    f"Elements of Phi node {stmt} do not all have the same dimensions"
                )

            if stmt.lhs not in type_env:
                # TODO: as above, this case can be triggered by a def-use cycle of plaintext values
                # raise TypeError(f"Cannot determine type of {stmt.lhs}")
                pass


def type_check(func: loop_linear_code.Function, dep_graph: DepGraph) -> TypeEnv:
    """
    Perform taint analysis to detect which variables are plaintext and which are shared.
    """

    type_env = TypeEnv(
        {
            # TODO: fix the below hack once parameter ssa renaming is properly implemented
            Var(param.var.name, 0): cast(VarType, param.var_type)
            for param in func.parameters
        }
    )
    _add_loop_counter_types(type_env, func.body)

    worklist = list(dep_graph.def_use_graph.nodes)

    while len(worklist) > 0:
        stmt = worklist.pop()
        if isinstance(stmt, loop_linear_code.Assign):
            if stmt.lhs in type_env:
                # This assignment has been reached before, don't extend the worklist
                continue

            if stmt.lhs.name in type_env:
                print(
                    f"[WARNING] Variable {stmt.lhs.name} is assigned multiple times in SSA",
                    file=sys.stderr,
                )

            var_type = _type_assign_expr(stmt.rhs, type_env)
            if var_type is None:
                # This variable cannot be typed yet
                continue

            assert stmt.lhs not in type_env
            type_env[stmt.lhs] = var_type

        elif isinstance(stmt, loop_linear_code.Phi):
            if stmt.lhs not in type_env:
                # This assignment has been reached before, don't extend the worklist
                continue

            if stmt.lhs.name in type_env:
                print(
                    f"[WARNING] Variable {stmt.lhs.name} is assigned multiple times in SSA",
                    file=sys.stderr,
                )

            elem_types = [_type_assign_expr(elem, type_env) for elem in stmt.rhs]
            elem_dims = [
                elem_type.dims for elem_type in elem_types if elem_type is not None
            ]

            if len(elem_dims) == 0:
                # We can't determine the dimensions of the returned value yet
                continue
            elif len(set(elem_dims)) > 1:
                raise TypeError(
                    "Phi expressions must have the same dimensions for all operands"
                )

            if all(
                elem_type is not None and elem_type.is_plaintext()
                for elem_type in elem_types
            ):
                var_type = VarType(VarVisibility.PLAINTEXT, elem_dims[0])
            elif any(
                elem_type is not None and elem_type.is_shared()
                for elem_type in elem_types
            ):
                var_type = VarType(VarVisibility.SHARED, elem_dims[0])
            else:
                # This variable cannot be typed yet
                continue

            type_env[stmt.lhs] = var_type
        else:
            raise AssertionError(
                f"Unexpected node {type(stmt)} added to type inference worklist"
            )

        # If we get to this point, the lhs has been reassigned so we must add dependencies
        # to the worklist
        worklist.extend([edge[1] for edge in dep_graph.def_use_graph.edges(stmt)])

    validate_type_requirements(func.body, type_env)

    return type_env
