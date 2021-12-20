import sys
from typing import Optional, Union

import networkx  # type: ignore

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
)
from .tac_cfg import AssignRHS, List, Tuple, Mux, Update


def _type_assign_rhs(
    rhs: Union[AssignRHS, SubscriptIndex], type_env: dict[str, VarType]
) -> Optional[VarType]:
    """
    Determines the type of an expression in a given type environment.  If an expression
    cannot be typed, this function returns None.
    """

    if isinstance(rhs, Var):
        return type_env.get(rhs.name)
    elif isinstance(rhs, ConstantInt):
        return VarType.PLAINTEXT
    elif isinstance(rhs, Subscript):
        if _type_assign_rhs(rhs.index, type_env) == VarType.SHARED:
            # TODO: switch this to a syntax error with the location of the offending
            # code in the original source code
            raise TypeError(f"Array subscript index {rhs.index} is not plaintext")
        return type_env.get(rhs.array.name)
    elif isinstance(rhs, BinOp):
        if (
            _type_assign_rhs(rhs.left, type_env) == VarType.PLAINTEXT
            and _type_assign_rhs(rhs.right, type_env) == VarType.PLAINTEXT
        ):
            return VarType.PLAINTEXT
        elif (
            _type_assign_rhs(rhs.left, type_env) == VarType.SHARED
            or _type_assign_rhs(rhs.right, type_env) == VarType.SHARED
        ):
            return VarType.SHARED
        else:
            return None
    elif isinstance(rhs, UnaryOp):
        return _type_assign_rhs(rhs.operand, type_env)
    elif isinstance(rhs, List) or isinstance(rhs, Tuple):
        if all(
            _type_assign_rhs(item, type_env) == VarType.PLAINTEXT for item in rhs.items
        ):
            return VarType.PLAINTEXT
        elif any(
            _type_assign_rhs(item, type_env) == VarType.SHARED for item in rhs.items
        ):
            return VarType.SHARED
        else:
            return None
    elif isinstance(rhs, Mux):
        return VarType.SHARED
    elif isinstance(rhs, Update):
        # TODO: what is the return value of Update()?
        # TODO: do Update statements need to update the type of the array?
        return None

    raise AssertionError(f"Unexpected type {type(rhs)} passed to _type_assign_rhs")


def _add_loop_counter_types(
    type_env: dict[str, VarType], stmts: list[loop_linear_code.Statement]
) -> None:
    """
    Adds the types of the loop counters to the type environment.
    """
    for stmt in stmts:
        if isinstance(stmt, loop_linear_code.For):
            type_env[stmt.counter.name] = VarType.PLAINTEXT
            _add_loop_counter_types(type_env, stmt.body)


def validate_type_requirements(
    stmts: list[loop_linear_code.Statement], type_env: dict[str, VarType]
) -> None:
    """
    Validates that all of MPC's type requirements are met.  Specifically, this function
    checks that all loop counters and array subscript indices are plaintext.
    """
    for stmt in stmts:
        if isinstance(stmt, loop_linear_code.For):
            if type_env[stmt.counter.name] != VarType.PLAINTEXT:
                raise TypeError(f"Loop counter {stmt.counter.name} is not plaintext")
            validate_type_requirements(stmt.body, type_env)
        elif isinstance(stmt, loop_linear_code.Assign):
            # The type assignment function checks for type errors internally
            _type_assign_rhs(stmt.rhs, type_env)


def loop_linear_add_types(
    func: loop_linear_code.Function, dep_graph: DepGraph
) -> loop_linear_code.Function:
    """
    Perform taint analysis to detect which variables are plaintext and which are shared.
    """

    var_types: dict[str, VarType] = {
        # TODO: fix the below hack once parameter ssa renaming is properly implemented
        f"{var.name}!0": var.var_type
        for var in func.parameters
    }
    _add_loop_counter_types(var_types, func.body)

    worklist = list(dep_graph.def_use_graph.nodes)

    while len(worklist) > 0:
        stmt = worklist.pop()
        if isinstance(stmt, loop_linear_code.Assign):
            if stmt.lhs.var_type is not None:
                # This assignment has been reached before, don't extend the worklist
                continue

            if stmt.lhs.name in var_types:
                print(
                    f"[WARNING] Variable {stmt.lhs.name} is assigned multiple times in SSA",
                    file=sys.stderr,
                )

            var_type = _type_assign_rhs(stmt.rhs, var_types)
            if var_type is None:
                # This variable cannot be typed yet
                continue

            stmt.lhs = Var(stmt.lhs.name, var_type)
            assert stmt.lhs.var_type is not None
            var_types[stmt.lhs.name] = stmt.lhs.var_type

        elif isinstance(stmt, loop_linear_code.Phi):
            if stmt.lhs.var_type is not None:
                # This assignment has been reached before, don't extend the worklist
                continue

            if stmt.lhs.name in var_types:
                print(
                    f"[WARNING] Variable {stmt.lhs.name} is assigned multiple times in SSA",
                    file=sys.stderr,
                )

            if all(var_types.get(var.name) == VarType.PLAINTEXT for var in stmt.rhs):
                stmt.lhs = Var(stmt.lhs.name, VarType.PLAINTEXT)
            elif any(var_types.get(var.name) == VarType.SHARED for var in stmt.rhs):
                stmt.lhs = Var(stmt.lhs.name, VarType.SHARED)
            else:
                # This variable cannot be typed yet
                continue

            assert stmt.lhs.var_type is not None
            var_types[stmt.lhs.name] = stmt.lhs.var_type
        else:
            raise AssertionError(
                f"Unexpected node {type(stmt)} added to type inference worklist"
            )

        # If we get to this point, the lhs has been reassigned so we must add dependencies
        # to the worklist
        worklist.extend([edge[1] for edge in dep_graph.def_use_graph.edges(stmt)])

    validate_type_requirements(func.body, var_types)

    return func
