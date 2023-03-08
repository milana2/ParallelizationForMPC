import os
from textwrap import indent
from typing import Union

from ...util import assert_never
from ...loop_linear_code import (
    Function,
    Statement,
    Phi,
    Assign,
    For,
    Return,
    Update,
    VectorizedAccess,
    VectorizedUpdate,
    Var,
    BinOp,
    BinOpKind,
    SubscriptIndexBinOp,
    List,
    Tuple,
    Mux,
    UnaryOp,
    UnaryOpKind,
    Subscript,
    SubscriptIndex,
    SubscriptIndexBinOp,
    SubscriptIndexUnaryOp,
    Atom,
    LiftExpr,
    DropDim,
)
from ...type_analysis import TypeEnv, Constant


def render_var(var: Var, var_mappings: dict[Var, str]) -> str:
    try:
        return var_mappings[var]
    except KeyError:
        return str(var).replace("!", "_")


def render_vectorized_access(v: VectorizedAccess, var_mappings: dict[Var, str]) -> str:
    num_dims = len(v.dim_sizes)
    idxs = v.idx_vars
    slice_indices: list[str] = []
    for dim in range(num_dims):
        if v.vectorized_dims[dim]:
            slice_indices.append("None")
        else:
            slice_indices.append(render_var(idxs[0], var_mappings))
            idxs = idxs[1:]
    array = render_var(v.array, var_mappings)
    slice = ", ".join(slice_indices)
    return f"{array}.get_vector_by_indices({slice})"


def render_atom(atom: Atom, var_mappings: dict[Var, str]) -> str:
    if isinstance(atom, Var):
        return render_var(atom, var_mappings)
    elif isinstance(atom, Constant):
        return str(atom)
    elif isinstance(atom, VectorizedAccess):
        return render_vectorized_access(atom, var_mappings)
    else:
        assert_never(atom)


def render_bin_op_kind(op: BinOpKind) -> str:
    if op == BinOpKind.AND:
        return "&"
    elif op == BinOpKind.OR:
        return "|"
    else:
        return str(op)


def render_unary_op_kind(op: UnaryOpKind) -> str:
    if op == UnaryOpKind.NEGATE:
        return "-"
    elif op == UnaryOpKind.NOT:
        return "~"
    else:
        assert_never(op)


def render_subscript_index(index: SubscriptIndex, var_mappings: dict[Var, str]) -> str:
    if isinstance(index, (Var, Constant)):
        return render_atom(index, var_mappings)
    elif isinstance(index, SubscriptIndexBinOp):
        left = render_subscript_index(index.left, var_mappings)
        operator = render_bin_op_kind(index.operator)
        right = render_subscript_index(index.right, var_mappings)
        return f"({left} {operator} {right})"
    elif isinstance(index, SubscriptIndexUnaryOp):
        operator = render_unary_op_kind(index.operator)
        operand = render_subscript_index(index.operand, var_mappings)
        return f"({operator}{operand})"
    else:
        assert_never(index)


def render_lift_expr(lift: LiftExpr) -> str:
    assert not isinstance(lift.expr, (Update, VectorizedUpdate))
    expr = render_assign_rhs(
        lift.expr,
        {var: f"indices[{index}]" for index, (var, _) in enumerate(lift.dims)},
    )
    dim_sizes = ", ".join([render_atom(size, dict()) for (_, size) in lift.dims])
    return f"lift(lambda indices: {expr}, [{dim_sizes}])"


def render_assign_rhs(
    arhs: Union[Atom, Subscript, BinOp, UnaryOp, List, Tuple, Mux, LiftExpr, DropDim],
    var_mappings: dict[Var, str],
) -> str:
    if isinstance(arhs, BinOp):
        left = render_assign_rhs(arhs.left, var_mappings)
        right = render_assign_rhs(arhs.right, var_mappings)
        return f"({left} {arhs.operator} {right})"
    elif isinstance(arhs, (Var, Constant, VectorizedAccess)):
        return render_atom(arhs, var_mappings)
    elif isinstance(arhs, List):
        items = [render_assign_rhs(item, var_mappings) for item in arhs.items]
        comma_separated_items = ", ".join(items)
        return f"[{comma_separated_items}]"
    elif isinstance(arhs, Tuple):
        items = [render_assign_rhs(item, var_mappings) + "," for item in arhs.items]
        return f"({items})"
    elif isinstance(arhs, Mux):
        condition = render_assign_rhs(arhs.condition, var_mappings)
        true_value = render_assign_rhs(arhs.true_value, var_mappings)
        false_value = render_assign_rhs(arhs.false_value, var_mappings)
        return f"{condition}.if_else({true_value}, {false_value})"
    elif isinstance(arhs, UnaryOp):
        operator = render_unary_op_kind(arhs.operator)
        operand = render_assign_rhs(arhs.operand, var_mappings)
        return f"({operator}{operand})"
    elif isinstance(arhs, Subscript):
        array = render_assign_rhs(arhs.array, var_mappings)
        index = render_subscript_index(arhs.index, var_mappings)
        return f"({array}[{index}])"
    elif isinstance(arhs, LiftExpr):
        return render_lift_expr(arhs)
    elif isinstance(arhs, DropDim):
        array = render_var(arhs.array, var_mappings)
        return f"drop_dim({array})"
    else:
        return assert_never(arhs)


def render_statement(stmt: Statement) -> str:
    if isinstance(stmt, Phi):
        return ""
    elif isinstance(stmt, Assign):
        lhs = render_atom(stmt.lhs, dict())
        if isinstance(stmt.rhs, Update):
            array = render_var(stmt.rhs.array, dict())
            index = render_subscript_index(stmt.rhs.index, dict())
            value = render_atom(stmt.rhs.value, dict())
            return f"{array}[{index}] = {value}; {lhs} = {array}"
        elif isinstance(stmt.rhs, VectorizedUpdate):
            access = render_vectorized_access(
                VectorizedAccess(
                    array=stmt.rhs.array,
                    dim_sizes=stmt.rhs.dim_sizes,
                    vectorized_dims=stmt.rhs.vectorized_dims,
                    idx_vars=stmt.rhs.idx_vars,
                ),
                dict(),
            )
            value = render_atom(stmt.rhs.value, dict())
            array = render_var(stmt.rhs.array, dict())
            return f"{access} = {value}; {lhs} = {array}"
        else:
            rhs = render_assign_rhs(stmt.rhs, dict())
            return f"{lhs} = {rhs}"
    elif isinstance(stmt, For):
        counter = render_var(stmt.counter, dict())
        bound_low = render_atom(stmt.bound_low, dict())
        bound_high = render_atom(stmt.bound_high, dict())
        body = indent(
            "\n".join([str(render_statement(body_stmt)) for body_stmt in stmt.body]),
            "    ",
        )
        return f"for {counter} in range({bound_low}, {bound_high}):\n{body}"
    elif isinstance(stmt, Return):
        value = render_var(stmt.value, dict())
        return f"return {value}"
    else:
        assert_never(stmt)


def render_statements(stmts: list[Statement]) -> str:
    return "\n".join(render_statement(stmt) for stmt in stmts)


def render_application(
    func: Function, type_env: TypeEnv, ran_vectorization: bool
) -> None:
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    )

    assert isinstance(func.body[-1], Return)
    return_type = type_env[func.body[-1].value]

    params = ", ".join(str(param.var) for param in func.parameters)
    func_def = f"def {func.name}({params}):"