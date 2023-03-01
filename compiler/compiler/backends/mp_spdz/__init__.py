import os

from compiler.compiler.ast_shared import BinOpKind

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
    Var,
    AssignRHS,
    BinOp,
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
)
from ...type_analysis import TypeEnv, VarVisibility, Constant, DataType


def render_var(var: Var) -> str:
    return str(var).replace("!", "_")


def render_atom(atom: Atom) -> str:
    if isinstance(atom, Var):
        return render_var(atom)
    elif isinstance(atom, Constant):
        return str(atom)
    elif isinstance(atom, VectorizedAccess):
        array = render_var(atom.array)
        dim_sizes = (
            "["
            + ", ".join([render_atom(dim_size) for dim_size in atom.dim_sizes])
            + "]"
        )
        idxs = "[" + ", ".join([render_var(idx) for idx in atom.idx_vars]) + "]"
        vectorized_dims = str(list(atom.vectorized_dims))
        return f"vectorized_access({array}, {dim_sizes}, {vectorized_dims}, {idxs})"
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


def render_subscript_index(index: SubscriptIndex) -> str:
    if isinstance(index, (Var, Constant)):
        return render_atom(index)
    elif isinstance(index, SubscriptIndexBinOp):
        left = render_subscript_index(index.left)
        operator = render_bin_op_kind(index.operator)
        right = render_subscript_index(index.right)
        return f"({left} {operator} {right})"
    elif isinstance(index, SubscriptIndexUnaryOp):
        operator = render_unary_op_kind(index.operator)
        operand = render_subscript_index(index.operand)
        return f"({operator}{operand})"
    else:
        assert_never(index)


def render_assign_rhs(expr: AssignRHS) -> str:
    if isinstance(expr, (BinOp, SubscriptIndexBinOp)):
        left = render_assign_rhs(expr.left)
        right = render_assign_rhs(expr.right)
        return f"({left} {expr.operator} {right})"
    elif isinstance(expr, (Var, Constant, VectorizedAccess)):
        return render_atom(expr)
    elif isinstance(expr, List):
        items = [render_assign_rhs(item) for item in expr.items]
        comma_separated_items = ", ".join(items)
        return f"[{comma_separated_items}]"
    elif isinstance(expr, Tuple):
        items = [render_assign_rhs(item) + "," for item in expr.items]
        return f"({items})"
    elif isinstance(expr, Mux):
        condition = render_assign_rhs(expr.condition)
        true_value = render_assign_rhs(expr.true_value)
        false_value = render_assign_rhs(expr.false_value)
        return f"{condition}.if_else({true_value}, {false_value})"
    elif isinstance(expr, UnaryOp):
        operator = render_unary_op_kind(expr.operator)
        operand = render_assign_rhs(expr.operand)
        return f"({operator}{operand})"
    elif isinstance(expr, Subscript):
        array = render_assign_rhs(expr.array)
        index = render_subscript_index(expr.index)
        return f"({array}[{index}])"
    elif isinstance(expr, Update):
        array = render_var(expr.array)
        index = render_subscript_index(expr.index)
        value = render_atom(expr.value)
        return f"({array}[:{index}] + [{value}] + {array}[{index}+1:])"
    else:
        return assert_never(expr)


def render_statement(stmt: Statement) -> str:
    if isinstance(stmt, Phi):
        pass
    elif isinstance(stmt, Assign):
        # If we're assigning to a vectorized value, use a specialized function for this.
        if isinstance(stmt.lhs, VectorizedAccess):
            pass
        elif isinstance(stmt.rhs, Update):
            pass
        else:
            lhs = render_var(stmt.lhs)
            rhs = render_assign_rhs(stmt.rhs)
            return f"{lhs} = {rhs}"
    elif isinstance(stmt, For):
        pass
    elif isinstance(stmt, Return):
        pass
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
