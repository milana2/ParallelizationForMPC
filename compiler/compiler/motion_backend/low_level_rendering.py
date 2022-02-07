import dataclasses as dc
from textwrap import indent
from typing import Optional, Union

from ..ast_shared import (
    BinOp,
    BinOpKind,
    Constant,
    DataType,
    Parameter,
    Subscript,
    TypeEnv,
    UnaryOp,
    UnaryOpKind,
    Var,
    VarType,
    VarVisibility,
)
from ..tac_cfg import Assign, AssignRHS, List, Mux, Tuple, Update
from ..util import assert_never
from ..loop_linear_code import For, Phi


@dc.dataclass(frozen=True)
class RenderOptions:
    type_env: TypeEnv
    plaintext: bool = False
    as_motion_input: bool = False


def render_type(var_type: VarType, plaintext: Optional[bool] = None) -> str:
    assert var_type.visibility is not None
    assert var_type.datatype is not None
    assert var_type.dims is not None

    if var_type.datatype == DataType.TUPLE:
        return (
            "std::tuple<"
            + ", ".join(render_type(t, plaintext) for t in var_type.tuple_types)
            + ">"
        )

    str_rep = ""
    for _ in range(var_type.dims):
        str_rep += "std::vector<"

    str_rep += render_datatype(
        var_type.datatype,
        plaintext=plaintext
        if plaintext is not None
        else var_type.visibility == VarVisibility.PLAINTEXT,
    )

    for _ in range(var_type.dims):
        str_rep += ">"

    return str_rep


def render_datatype(datatype: DataType, plaintext: bool) -> str:
    if datatype == DataType.INT:
        if plaintext:
            return "std::uint32_t"
        else:
            return "encrypto::motion::SecureUnsignedInteger"

    elif datatype == DataType.BOOL:
        if plaintext:
            return "bool"
        else:
            return "encrypto::motion::ShareWrapper"

    return assert_never(datatype)


def render_param(param: Parameter, type_env: TypeEnv) -> str:
    plaintext = param.var_type.is_plaintext()

    return (
        render_type(param.var_type, plaintext)
        + " "
        + render_expr(param.var, RenderOptions(type_env, plaintext=plaintext))
    )


def render_stmt(stmt: Union[Assign, For], type_env: TypeEnv) -> str:
    if isinstance(stmt, Assign):
        shared_assignment = (
            render_expr(stmt.lhs, RenderOptions(type_env, plaintext=False))
            + " = "
            + render_expr(stmt.rhs, RenderOptions(type_env, plaintext=False))
            + ";"
        )
        plaintext_assignment = (
            render_expr(stmt.lhs, RenderOptions(type_env, plaintext=True))
            + " = "
            + render_expr(stmt.rhs, RenderOptions(type_env, plaintext=True))
            + ";"
        )

        if (
            type_env[stmt.lhs].is_shared()
            or type_env[stmt.lhs].datatype == DataType.TUPLE
        ):
            return shared_assignment
        else:
            return shared_assignment + "\n" + plaintext_assignment

    elif isinstance(stmt, For):
        phi_initializations = "// Initialize phi values\n" + "\n".join(
            render_expr(phi.lhs, RenderOptions(type_env))
            + " = "
            + render_expr(phi.rhs_false, RenderOptions(type_env))
            + ";"
            for phi in stmt.body
            if isinstance(phi, Phi)
        )

        header = (
            "for ("
            + render_expr(stmt.counter, RenderOptions(type_env, plaintext=True))
            + " = "
            + render_expr(stmt.bound_low, RenderOptions(type_env, plaintext=True))
            + "; "
            + render_expr(stmt.counter, RenderOptions(type_env, plaintext=True))
            + " < "
            + render_expr(stmt.bound_high, RenderOptions(type_env, plaintext=True))
            + "; "
            + render_expr(stmt.counter, RenderOptions(type_env, plaintext=True))
            + "++) {"
        )

        body = (
            "\n".join(
                render_stmt(stmt, type_env)
                for stmt in stmt.body
                if not isinstance(stmt, Phi)
            )
            + "\n"
        )

        phi_updates = "// Update phi values\n" + "\n".join(
            render_expr(phi.lhs, RenderOptions(type_env))
            + " = "
            + render_expr(phi.rhs_true, RenderOptions(type_env))
            + ";"
            for phi in stmt.body
            if isinstance(phi, Phi)
        )

        return (
            "\n"
            + phi_initializations
            + "\n"
            + header
            + "\n"
            # Initialize loop counter for use in loop
            + f"    {render_expr(stmt.counter, RenderOptions(type_env))} = party->In<Protocol>(encrypto::motion::ToInput({render_expr(stmt.counter, RenderOptions(type_env, plaintext=True))}), 0);"
            + "\n"
            + indent(body, "    ")
            + "\n"
            + indent(phi_updates, "    ")
            + "\n}\n"
        )

    return assert_never(stmt)


def _render_operator(op: Union[BinOpKind, UnaryOpKind]) -> str:
    if op == BinOpKind.AND:
        return "&"

    if op == BinOpKind.OR:
        return "|"

    if op == BinOpKind.DIV:
        return "/"

    if op == UnaryOpKind.NOT:
        return "~"

    return str(op)


def render_expr(expr: Union[AssignRHS], opts: RenderOptions) -> str:
    if isinstance(expr, BinOp):
        if expr.operator == BinOpKind.LT:
            return render_expr(BinOp(expr.right, BinOpKind.GT, expr.left), opts)
        elif expr.operator == BinOpKind.NOT_EQ:
            return render_expr(
                UnaryOp(UnaryOpKind.NOT, BinOp(expr.left, BinOpKind.EQ, expr.right)),
                opts,
            )
        elif expr.operator == BinOpKind.LT_E:
            return (
                "("
                + render_expr(BinOp(expr.left, BinOpKind.LT, expr.right), opts)
                + " | "
                + render_expr(BinOp(expr.left, BinOpKind.EQ, expr.right), opts)
                + ")"
            )
        elif expr.operator == BinOpKind.GT_E:
            return (
                "("
                + render_expr(BinOp(expr.left, BinOpKind.GT, expr.right), opts)
                + " | "
                + render_expr(BinOp(expr.left, BinOpKind.EQ, expr.right), opts)
                + ")"
            )

        # If we're using an arithmetic primitive operation or we're operating on plaintext values,
        # don't cast to a share wrapper
        elif opts.plaintext or expr.operator in (
            BinOpKind.ADD,
            BinOpKind.SUB,
            BinOpKind.MUL,
            BinOpKind.DIV,
            BinOpKind.GT,
        ):
            return f"({render_expr(expr.left, opts)} {expr.operator.value} {render_expr(expr.right, opts)})"

        # Otherwise, convert to a ShareWrapper since they have more operators defined
        # TODO: go through the operators for ShareWrapper and make sure they're all valid
        # for the default protocol
        else:
            return (
                "("
                + (
                    "encrypto::motion::ShareWrapper("
                    + render_expr(expr.left, opts)
                    + ".Get())"
                    + " "
                    + _render_operator(expr.operator)
                    + " "
                    + "encrypto::motion::ShareWrapper("
                    + render_expr(expr.right, opts)
                    + ".Get())"
                )
                + ")"
            )

    elif isinstance(expr, Constant):
        if opts.as_motion_input:
            cpp_const = render_expr(
                expr, dc.replace(opts, plaintext=True, as_motion_input=False)
            )

            if expr.datatype == DataType.INT:
                return f"encrypto::motion::ToInput({cpp_const})"
            elif expr.datatype == DataType.BOOL:
                return f"encrypto::motion::BitVector(1, {cpp_const})"
            else:
                assert_never(expr)

        elif opts.plaintext:
            if expr.datatype == DataType.INT:
                return f"std::uint32_t({expr.value})"
            elif expr.datatype == DataType.BOOL:
                return str(expr).lower()
            else:
                assert_never(expr)

        else:
            return "_MPC_CONSTANT_" + str(expr).lower()

    elif isinstance(expr, List):
        items = ", ".join(render_expr(item, opts) for item in expr.items)
        return "{" + items + "}"

    elif isinstance(expr, Mux):
        if isinstance(expr.true_value, Var):
            true_shared = opts.type_env[expr.true_value].is_shared()
        elif isinstance(expr.true_value, Constant):
            true_shared = False
        else:
            true_shared = opts.type_env[expr.true_value.array].is_shared()

        if isinstance(expr.false_value, Var):
            false_shared = opts.type_env[expr.false_value].is_shared()
        elif isinstance(expr.false_value, Constant):
            false_shared = False
        else:
            false_shared = opts.type_env[expr.false_value.array].is_shared()

        cpp_cond = render_expr(expr.condition, opts)
        cpp_true_val = render_expr(expr.true_value, opts) + ".Get()"
        cpp_false_val = render_expr(expr.false_value, opts) + ".Get()"

        return f"{cpp_cond}.Mux({cpp_false_val}, {cpp_true_val})"

    elif isinstance(expr, Subscript):
        return f"{render_expr(expr.array, opts)}[{render_expr(expr.index, dc.replace(opts, plaintext=True))}]"

    elif isinstance(expr, Tuple):
        items = ", ".join(render_expr(item, opts) for item in expr.items)
        return f"std::make_tuple({items})"

    elif isinstance(expr, UnaryOp):
        return f"({_render_operator(expr.operator)}{render_expr(expr.operand, opts)})"

    elif isinstance(expr, Update):
        cpp_arr = render_expr(expr.array, opts)
        cpp_arr_access = render_expr(Subscript(expr.array, expr.index), opts)
        cpp_val = render_expr(expr.value, opts)
        return f"{cpp_arr};\n{cpp_arr_access} = {cpp_val}"

    elif isinstance(expr, Var):
        cpp_str = str(expr).replace("!", "_")
        if opts.plaintext:
            return f"_MPC_PLAINTEXT_{cpp_str}"
        else:
            return cpp_str

    return assert_never(expr)
