from copy import copy
import dataclasses as dc
from textwrap import indent
from typing import Optional, Union

from ..ast_shared import (
    BinOpKind,
    Constant,
    DataType,
    Parameter,
    Subscript,
    SubscriptIndex,
    SubscriptIndexBinOp,
    SubscriptIndexUnaryOp,
    TypeEnv,
    UnaryOpKind,
    Var,
    VarType,
    VarVisibility,
    VectorizedAccess,
)
from ..tac_cfg import (
    Assign,
    AssignRHS,
    BinOp,
    List,
    Mux,
    Tuple,
    UnaryOp,
    Update,
    VectorizedUpdate,
    LiftExpr,
    DropDim,
)
from ..util import assert_never
from ..loop_linear_code import For, Phi, Return
from ..type_analysis import type_assign_expr, PLAINTEXT_INT


@dc.dataclass(frozen=True)
class RenderContext:
    type_env: TypeEnv
    plaintext: bool = False
    as_motion_input: bool = False
    int_type: str = "std::uint32_t"
    var_mappings: dict[Var, str] = dc.field(default_factory=dict)


def render_type(var_type: VarType, plaintext: Optional[bool] = None) -> str:
    assert var_type.visibility is not None
    assert var_type.datatype is not None
    assert var_type.unvectorized_dims is not None

    if var_type.datatype == DataType.TUPLE:
        return (
            "std::tuple<"
            + ", ".join(render_type(t, plaintext) for t in var_type.tuple_types)
            + ">"
        )

    str_rep = ""
    if var_type.unvectorized_dims > 0:
        str_rep += "std::vector<"

    str_rep += render_datatype(
        var_type.datatype,
        plaintext=plaintext
        if plaintext is not None
        else var_type.visibility == VarVisibility.PLAINTEXT,
    )

    if var_type.unvectorized_dims > 0:
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

    raise NotImplementedError(f"Unsupported datatype: {datatype}")


def render_param(param: Parameter, type_env: TypeEnv) -> str:
    plaintext = param.var_type.is_plaintext()

    return (
        render_type(param.var_type, plaintext)
        + " "
        + render_expr(param.var, RenderContext(type_env, plaintext=plaintext))
    )


def render_stmt(stmt: Union[Assign, For, Return], type_env: TypeEnv) -> str:
    if isinstance(stmt, Assign):
        # If we're assigning to a vectorized value, use a specialized function for this.
        if isinstance(stmt.lhs, VectorizedAccess):
            ctx = RenderContext(type_env, plaintext=False)
            val_expr = render_expr(stmt.rhs, ctx)

            # If this isn't a true vectorized access, just subscript normally
            if all(vectorized == False for vectorized in stmt.lhs.vectorized_dims):
                lhs = render_expr(stmt.lhs, ctx)
                return f"{lhs} = {val_expr};"

            dim_sizes = (
                "{"
                + ", ".join(
                    render_expr(loop_bound, dc.replace(ctx, plaintext=True))
                    for loop_bound in stmt.lhs.dim_sizes
                )
                + "}"
            )
            vectorized_dims = (
                "{"
                + ", ".join(
                    str(vectorized).lower() for vectorized in stmt.lhs.vectorized_dims
                )
                + "}"
            )
            idxs = (
                "{"
                + ", ".join(
                    render_expr(var, dc.replace(ctx, plaintext=True))
                    for var, vectorized in zip(
                        stmt.lhs.idx_vars, stmt.lhs.vectorized_dims
                    )
                    if not vectorized
                )
                + "}"
            )

            return f"vectorized_assign({render_expr(stmt.lhs.array, ctx)}, {dim_sizes}, {vectorized_dims}, {idxs}, {val_expr});"
        else:
            shared_assignment = (
                render_expr(stmt.lhs, RenderContext(type_env, plaintext=False))
                + " = "
                + render_expr(stmt.rhs, RenderContext(type_env, plaintext=False))
                + ";"
            )
            plaintext_assignment = (
                render_expr(stmt.lhs, RenderContext(type_env, plaintext=True))
                + " = "
                + render_expr(stmt.rhs, RenderContext(type_env, plaintext=True))
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
        ctr_initializer = (
            "// Initialize loop counter\n"
            + render_expr(stmt.counter, RenderContext(type_env, plaintext=True))
            + " = "
            + render_expr(stmt.bound_low, RenderContext(type_env, plaintext=True))
            + ";"
        )

        phi_initializations = "// Initialize phi values\n" + "\n".join(
            render_stmt(Assign(phi.lhs, phi.rhs_false), type_env)
            for phi in stmt.body
            if isinstance(phi, Phi)
        )

        header = (
            "for (; "
            + render_expr(stmt.counter, RenderContext(type_env, plaintext=True))
            + " < "
            + render_expr(stmt.bound_high, RenderContext(type_env, plaintext=True))
            + "; "
            + render_expr(stmt.counter, RenderContext(type_env, plaintext=True))
            + "++) {"
        )

        phi_assignments = "\n".join(
            render_stmt(Assign(phi.lhs, phi.rhs_true), type_env)
            for phi in stmt.body
            if isinstance(phi, Phi)
        )

        phi_updates = (
            "// Update phi values\n"
            + "if ("
            + render_expr(stmt.counter, RenderContext(type_env, plaintext=True))
            + " != "
            + render_expr(stmt.bound_low, RenderContext(type_env, plaintext=True))
            + ") {\n"
            + indent(
                phi_assignments,
                "    ",
            )
            + "\n}\n"
        )

        body = (
            "\n".join(
                render_stmt(stmt, type_env)
                for stmt in stmt.body
                if not isinstance(stmt, Phi)
            )
            + "\n"
        )

        return (
            "\n"
            + ctr_initializer
            + "\n"
            + phi_initializations
            + "\n"
            + header
            + "\n"
            # Initialize loop counter for use in loop
            + f"    {render_expr(stmt.counter, RenderContext(type_env))} = party->In<Protocol>(encrypto::motion::ToInput({render_expr(stmt.counter, RenderContext(type_env, plaintext=True))}), 0);"
            + "\n"
            + indent(phi_updates, "    ")
            + "\n"
            + indent(body, "    ")
            + "\n}\n"
        )

    elif isinstance(stmt, Return):
        return (
            "return "
            + render_expr(stmt.value, RenderContext(type_env, plaintext=False))
            + ";"
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


def render_expr(expr: Union[AssignRHS, SubscriptIndex], ctx: RenderContext) -> str:
    if isinstance(expr, (BinOp, SubscriptIndexBinOp)):
        if expr.operator == BinOpKind.LT:
            return render_expr(
                dc.replace(
                    expr, left=expr.right, right=expr.left, operator=BinOpKind.GT
                ),
                ctx,
            )
        elif expr.operator == BinOpKind.NOT_EQ:
            if isinstance(expr, BinOp):
                return render_expr(
                    UnaryOp(UnaryOpKind.NOT, dc.replace(expr, operator=BinOpKind.EQ)),
                    ctx,
                )
            else:
                return render_expr(
                    SubscriptIndexUnaryOp(
                        UnaryOpKind.NOT, dc.replace(expr, operator=BinOpKind.EQ)
                    ),
                    ctx,
                )
        elif expr.operator == BinOpKind.LT_E:
            return (
                "("
                + render_expr(dc.replace(expr, operator=BinOpKind.LT), ctx)
                + " | "
                + render_expr(dc.replace(expr, operator=BinOpKind.EQ), ctx)
                + ")"
            )
        elif expr.operator == BinOpKind.GT_E:
            return (
                "("
                + render_expr(dc.replace(expr, operator=BinOpKind.GT), ctx)
                + " | "
                + render_expr(dc.replace(expr, operator=BinOpKind.EQ), ctx)
                + ")"
            )

        # If we're using an arithmetic primitive operation or we're operating on plaintext values,
        # don't cast to a share wrapper
        elif ctx.plaintext or expr.operator in (
            BinOpKind.ADD,
            BinOpKind.SUB,
            BinOpKind.MUL,
            BinOpKind.DIV,
            BinOpKind.GT,
        ):
            return f"({render_expr(expr.left, ctx)} {expr.operator.value} {render_expr(expr.right, ctx)})"

        # Otherwise, convert to a ShareWrapper since they have more operators defined
        # TODO: go through the operators for ShareWrapper and make sure they're all valid
        # for the default protocol
        else:
            return (
                "("
                + (
                    "encrypto::motion::ShareWrapper("
                    + render_expr(expr.left, ctx)
                    + ".Get())"
                    + " "
                    + _render_operator(expr.operator)
                    + " "
                    + "encrypto::motion::ShareWrapper("
                    + render_expr(expr.right, ctx)
                    + ".Get())"
                )
                + ")"
            )

    elif isinstance(expr, Constant):
        if ctx.as_motion_input:
            cpp_const = render_expr(
                expr, dc.replace(ctx, plaintext=True, as_motion_input=False)
            )

            if expr.datatype == DataType.INT:
                return f"encrypto::motion::ToInput({cpp_const})"
            elif expr.datatype == DataType.BOOL:
                return f"encrypto::motion::BitVector(1, {cpp_const})"
            else:
                raise NotImplementedError(f"Unsupported datatype: {expr.datatype}")

        elif ctx.plaintext:
            if expr.datatype == DataType.INT:
                return f"{ctx.int_type}({expr.value})"
            elif expr.datatype == DataType.BOOL:
                return str(expr).lower()
            else:
                raise NotImplementedError(f"Unsupported datatype: {expr.datatype}")

        else:
            return "_MPC_CONSTANT_" + str(expr).lower()

    elif isinstance(expr, DropDim):
        dims = (
            "{"
            + ", ".join(
                render_expr(loop_bound, dc.replace(ctx, plaintext=True))
                for loop_bound in expr.dims
            )
            + "}"
        )
        # Since we want to manipulate the array, we don't want the input to drop_dim()
        # to be vectorized
        if isinstance(expr.array, VectorizedAccess):
            array = render_expr(expr.array.array, ctx)
        else:
            array = render_expr(expr.array, ctx)

        specialization = ""
        # If the returned array will be of size 1, then we need to use a specialized form of drop_dim()
        if len(expr.dims) == 1:
            specialization = "_monoreturn"

        return f"drop_dim{specialization}({array}, {dims})"

    elif isinstance(expr, List):
        items = ", ".join(render_expr(item, ctx) for item in expr.items)
        return "{" + items + "}"

    elif isinstance(expr, Mux):
        cpp_cond = render_expr(expr.condition, ctx)
        cpp_true_val = render_expr(expr.true_value, ctx) + ".Get()"
        cpp_false_val = render_expr(expr.false_value, ctx) + ".Get()"

        return f"{cpp_cond}.Mux({cpp_false_val}, {cpp_true_val})"

    elif isinstance(expr, LiftExpr):
        raw_idx_map = lambda idx: f"indices[{idx}]"
        augmented_env = copy(ctx.type_env)
        for idx_var, _dim_size in expr.dims:
            augmented_env[idx_var] = PLAINTEXT_INT
        if (
            not ctx.plaintext
            and type_assign_expr(expr.expr, augmented_env).is_plaintext()
        ):
            if type_assign_expr(expr.expr, augmented_env).datatype == DataType.INT:
                idx_type_conversion = (
                    lambda val: f"encrypto::motion::SecureUnsignedInteger({val})"
                )
            else:
                idx_type_conversion = lambda val: val

            to_shared = (
                lambda val: f"party->In<Protocol>(encrypto::motion::ToInput({val}), 0)"
            )

            idx_map = lambda idx: idx_type_conversion(to_shared(raw_idx_map(idx)))
        else:
            idx_map = raw_idx_map

        inner_ctx = dc.replace(
            ctx,
            int_type="std::uint32_t",
            var_mappings={var: idx_map(i) for i, (var, _) in enumerate(expr.dims)},
        )
        inner_expr = f"std::function([&](const std::vector<std::uint32_t> &indices){{return {render_expr(expr.expr, inner_ctx)};}})"

        dims = (
            "{"
            + ", ".join(
                render_expr(loop_bound, dc.replace(ctx, plaintext=True))
                for _, loop_bound in expr.dims
            )
            + "}"
        )

        return f"lift({inner_expr}, {dims})"

    elif isinstance(expr, Subscript):
        return f"{render_expr(expr.array, ctx)}[{render_expr(expr.index, dc.replace(ctx, plaintext=True))}]"

    elif isinstance(expr, Tuple):
        items = ", ".join(render_expr(item, ctx) for item in expr.items)
        return f"std::make_tuple({items})"

    elif isinstance(expr, (UnaryOp, SubscriptIndexUnaryOp)):
        return f"({_render_operator(expr.operator)}{render_expr(expr.operand, ctx)})"

    elif isinstance(expr, Update):
        cpp_arr = render_expr(expr.array, ctx)
        cpp_arr_access = render_expr(Subscript(expr.array, expr.index), ctx)
        cpp_val = render_expr(expr.value, ctx)
        return f"{cpp_arr};\n{cpp_arr_access} = {cpp_val}"

    elif isinstance(expr, Var):
        if expr in ctx.var_mappings:
            return ctx.var_mappings[expr]

        cpp_str = str(expr).replace("!", "_")
        if ctx.plaintext:
            return f"_MPC_PLAINTEXT_{cpp_str}"
        else:
            return cpp_str

    elif isinstance(expr, VectorizedAccess):
        # If this isn't a true vectorized access, just subscript normally
        if all(vectorized == False for vectorized in expr.vectorized_dims):
            subscript = " + ".join(
                f"({render_expr(idx, dc.replace(ctx, plaintext=True))} * "
                + "*".join(
                    render_expr(bound, dc.replace(ctx, plaintext=True))
                    for bound in expr.dim_sizes[dim + 1 :]
                )
                + ")"
                # Skip the last dimension for now since it doesn't get multiplied
                for dim, idx in enumerate(expr.idx_vars[:-1])
            )

            # Since the last dimension has no multiplicative factor, render it separately
            if subscript:
                subscript += " + "
            subscript += render_expr(expr.idx_vars[-1], dc.replace(ctx, plaintext=True))
            return f"{render_expr(expr.array, ctx)}[{subscript}]"

        dim_sizes = (
            "{"
            + ", ".join(
                render_expr(loop_bound, dc.replace(ctx, plaintext=True))
                for loop_bound in expr.dim_sizes
            )
            + "}"
        )
        vectorized_dims = (
            "{"
            + ", ".join(str(vectorized).lower() for vectorized in expr.vectorized_dims)
            + "}"
        )
        idxs = (
            "{"
            + ", ".join(
                render_expr(var, dc.replace(ctx, plaintext=True))
                for var, vectorized in zip(expr.idx_vars, expr.vectorized_dims)
                if not vectorized
            )
            + "}"
        )
        return f"vectorized_access({render_expr(expr.array, ctx)}, {dim_sizes}, {vectorized_dims}, {idxs})"

    elif isinstance(expr, VectorizedUpdate):
        # If this isn't a true vectorized access, just subscript normally
        if all(vectorized == False for vectorized in expr.vectorized_dims):
            subscript = " + ".join(
                f"({render_expr(idx, dc.replace(ctx, plaintext=True))} * "
                + "*".join(
                    render_expr(bound, dc.replace(ctx, plaintext=True))
                    for bound in expr.dim_sizes[dim + 1 :]
                )
                + ")"
                # Skip the last dimension for now since it doesn't get multiplied
                for dim, idx in enumerate(expr.idx_vars[:-1])
            )

            # Since the last dimension has no multiplicative factor, render it separately
            if subscript:
                subscript += " + "
            subscript += render_expr(expr.idx_vars[-1], dc.replace(ctx, plaintext=True))
            return f"{render_expr(expr.array, ctx)}[{subscript}]"

        dim_sizes = (
            "{"
            + ", ".join(
                render_expr(loop_bound, dc.replace(ctx, plaintext=True))
                for loop_bound in expr.dim_sizes
            )
            + "}"
        )
        vectorized_dims = (
            "{"
            + ", ".join(str(vectorized).lower() for vectorized in expr.vectorized_dims)
            + "}"
        )
        idxs = (
            "{"
            + ", ".join(
                render_expr(var, dc.replace(ctx, plaintext=True))
                for var, vectorized in zip(expr.idx_vars, expr.vectorized_dims)
                if not vectorized
            )
            + "}"
        )
        return f"vectorized_update({render_expr(expr.array, ctx)}, {dim_sizes}, {vectorized_dims}, {idxs}, {render_expr(expr.value, ctx)})"

    return assert_never(expr)
