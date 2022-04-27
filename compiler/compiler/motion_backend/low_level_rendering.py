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
    enclosing_loops: list[For] = dc.field(default_factory=list)


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


def collect_plaintext_conversions(expr: AssignRHS, type_env: TypeEnv) -> list[Var]:
    if isinstance(expr, Var):
        if type_env[expr].is_plaintext():
            return [expr]
        else:
            return []
    elif isinstance(expr, UnaryOp):
        return collect_plaintext_conversions(expr.operand, type_env)
    elif isinstance(expr, BinOp):
        return collect_plaintext_conversions(
            expr.left, type_env
        ) + collect_plaintext_conversions(expr.right, type_env)
    elif isinstance(expr, (List, Tuple)):
        return [
            var
            for elem in expr.items
            for var in collect_plaintext_conversions(elem, type_env)
        ]
    elif isinstance(expr, (Update, VectorizedUpdate)):
        return collect_plaintext_conversions(expr.value, type_env)
    elif isinstance(expr, Mux):
        return (
            collect_plaintext_conversions(expr.condition, type_env)
            + collect_plaintext_conversions(expr.true_value, type_env)
            + collect_plaintext_conversions(expr.false_value, type_env)
        )
    elif isinstance(expr, LiftExpr):
        return collect_plaintext_conversions(expr.expr, type_env)
    # The below expressions never require conversion to plaintext
    elif isinstance(expr, (Constant, Subscript, VectorizedAccess, DropDim)):
        return []
    else:
        assert_never(expr)


def render_stmt(
    stmt: Union[Assign, For, Return],
    type_env: TypeEnv,
    ran_vectorization: bool,
    enclosing_loops=[],
) -> str:
    if isinstance(stmt, Assign):
        # Convert any plaintext assignments
        plaintext_conversions = ""
        if (
            type_assign_expr(stmt.lhs, type_env, stmt, None).is_shared()
            # lift expressions are always shared, even if they're lifting to "plaintext" arrays
            or isinstance(stmt.rhs, LiftExpr)
        ):
            vars_needing_conversions = collect_plaintext_conversions(stmt.rhs, type_env)
            plaintext_conversions = "\n".join(
                render_expr(
                    var,
                    RenderContext(
                        type_env, plaintext=False, enclosing_loops=enclosing_loops
                    ),
                )
                + " = party->In<Protocol>("
                + render_expr(
                    var,
                    RenderContext(
                        type_env,
                        as_motion_input=True,
                        enclosing_loops=enclosing_loops,
                    ),
                )
                + ", 0);"
                for var in vars_needing_conversions
            )

            if plaintext_conversions:
                plaintext_conversions += "\n"

        # If we're assigning to a vectorized value, use a specialized function for this.
        if isinstance(stmt.lhs, VectorizedAccess):
            ctx = RenderContext(
                type_env, plaintext=False, enclosing_loops=enclosing_loops
            )
            val_expr = render_expr(stmt.rhs, ctx)

            # If this isn't a true vectorized access, just subscript normally
            if all(vectorized == False for vectorized in stmt.lhs.vectorized_dims):
                lhs = render_expr(stmt.lhs, ctx)
                return plaintext_conversions + f"{lhs} = {val_expr};"

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

            return (
                plaintext_conversions
                + f"vectorized_assign({render_expr(stmt.lhs.array, ctx)}, {dim_sizes}, {vectorized_dims}, {idxs}, {val_expr});"
            )

        if isinstance(stmt.rhs, Update):
            shared_assignment = (
                (
                    render_expr(
                        stmt.rhs,
                        RenderContext(
                            type_env, plaintext=False, enclosing_loops=enclosing_loops
                        ),
                    )
                    + ";\n"
                )
                + render_expr(
                    stmt.lhs,
                    RenderContext(
                        type_env, plaintext=False, enclosing_loops=enclosing_loops
                    ),
                )
                + " = "
                + render_expr(
                    stmt.rhs.array,
                    RenderContext(
                        type_env, plaintext=False, enclosing_loops=enclosing_loops
                    ),
                )
                + ";"
            )
            plaintext_assignment = (
                (
                    render_expr(
                        stmt.rhs,
                        RenderContext(
                            type_env, plaintext=True, enclosing_loops=enclosing_loops
                        ),
                    )
                    + ";\n"
                )
                + render_expr(
                    stmt.lhs,
                    RenderContext(
                        type_env, plaintext=True, enclosing_loops=enclosing_loops
                    ),
                )
                + " = "
                + render_expr(
                    stmt.rhs.array,
                    RenderContext(
                        type_env, plaintext=True, enclosing_loops=enclosing_loops
                    ),
                )
                + ";"
            )

        else:
            shared_assignment = (
                render_expr(
                    stmt.lhs,
                    RenderContext(
                        type_env, plaintext=False, enclosing_loops=enclosing_loops
                    ),
                )
                + " = "
                + render_expr(
                    stmt.rhs,
                    RenderContext(
                        type_env, plaintext=False, enclosing_loops=enclosing_loops
                    ),
                )
                + ";"
            )
            plaintext_assignment = (
                render_expr(
                    stmt.lhs,
                    RenderContext(
                        type_env, plaintext=True, enclosing_loops=enclosing_loops
                    ),
                )
                + " = "
                + render_expr(
                    stmt.rhs,
                    RenderContext(
                        type_env, plaintext=True, enclosing_loops=enclosing_loops
                    ),
                )
                + ";"
            )

        if (
            type_env[stmt.lhs].is_shared()
            or type_env[stmt.lhs].datatype == DataType.TUPLE
        ):
            return plaintext_conversions + shared_assignment
        else:
            return plaintext_conversions + plaintext_assignment

    elif isinstance(stmt, For):
        ctr_initializer = (
            "// Initialize loop counter\n"
            + render_expr(
                stmt.counter,
                RenderContext(
                    type_env, plaintext=True, enclosing_loops=enclosing_loops
                ),
            )
            + " = "
            + render_expr(
                stmt.bound_low,
                RenderContext(
                    type_env, plaintext=True, enclosing_loops=enclosing_loops
                ),
            )
            + ";"
        )

        phi_initializations = "// Initialize phi values\n" + "\n".join(
            render_stmt(Assign(phi.lhs, phi.rhs_false), type_env, ran_vectorization)
            for phi in stmt.body
            if isinstance(phi, Phi)
        )

        header = (
            "for (; "
            + render_expr(
                stmt.counter,
                RenderContext(
                    type_env, plaintext=True, enclosing_loops=enclosing_loops
                ),
            )
            + " < "
            + render_expr(
                stmt.bound_high,
                RenderContext(
                    type_env, plaintext=True, enclosing_loops=enclosing_loops
                ),
            )
            + "; "
            + render_expr(
                stmt.counter,
                RenderContext(
                    type_env, plaintext=True, enclosing_loops=enclosing_loops
                ),
            )
            + "++) {"
        )

        phi_assignments = "\n".join(
            render_stmt(Assign(phi.lhs, phi.rhs_true), type_env, ran_vectorization)
            for phi in stmt.body
            if isinstance(phi, Phi)
        )

        phi_updates = (
            "// Update phi values\n"
            + "if ("
            + render_expr(
                stmt.counter,
                RenderContext(
                    type_env, plaintext=True, enclosing_loops=enclosing_loops
                ),
            )
            + " != "
            + render_expr(
                stmt.bound_low,
                RenderContext(
                    type_env, plaintext=True, enclosing_loops=enclosing_loops
                ),
            )
            + ") {\n"
            + indent(
                phi_assignments,
                "    ",
            )
            + "\n}\n"
        )

        body = (
            "\n".join(
                render_stmt(
                    substmt, type_env, ran_vectorization, enclosing_loops + [stmt]
                )
                for substmt in stmt.body
                if not isinstance(substmt, Phi)
            )
            + "\n"
        )

        if not ran_vectorization:
            phi_finalizations = "// Assign final phi values\n" + phi_assignments + "\n"
        else:
            phi_finalizations = ""

        return (
            "\n"
            + ctr_initializer
            + "\n"
            + phi_initializations
            + "\n"
            + header
            + "\n"
            + indent(phi_updates, "    ")
            + "\n"
            + indent(body, "    ")
            + "\n}\n"
            + phi_finalizations
        )

    elif isinstance(stmt, Return):
        return (
            "return "
            + render_expr(
                stmt.value,
                RenderContext(
                    type_env, plaintext=False, enclosing_loops=enclosing_loops
                ),
            )
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
    if ctx.as_motion_input:
        cpp_var = render_expr(
            expr, dc.replace(ctx, plaintext=True, as_motion_input=False)
        )

        if type_assign_expr(expr, ctx.type_env, None, None).datatype == DataType.INT:
            return f"encrypto::motion::ToInput({cpp_var})"
        elif type_assign_expr(expr, ctx.type_env, None, None).datatype == DataType.BOOL:
            return f"encrypto::motion::BitVector(1, {cpp_var})"
        else:
            raise NotImplementedError(
                f"Unsupported datatype: {type_assign_expr(expr, ctx.type_env, None, None).datatype}"
            )

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

        operand_dims = None
        if isinstance(expr.left, VectorizedAccess):
            operand_dims = tuple(
                (idx_var, dim_size)
                for idx_var, dim_size, vectorized in zip(
                    expr.left.idx_vars,
                    expr.left.dim_sizes,
                    expr.left.vectorized_dims,
                )
                if vectorized
            )
        elif isinstance(expr.right, VectorizedAccess):
            operand_dims = tuple(
                (idx_var, dim_size)
                for idx_var, dim_size, vectorized in zip(
                    expr.right.idx_vars,
                    expr.right.dim_sizes,
                    expr.right.vectorized_dims,
                )
                if vectorized
            )

        if operand_dims and isinstance(expr.left, (Constant, Var)):
            lift_expr = LiftExpr(expr.left, operand_dims)
            left_expr = f"decltype({render_expr(expr.left, ctx)})::Simdify({render_expr(lift_expr, ctx)})"
        else:
            left_expr = render_expr(expr.left, ctx)

        if operand_dims and isinstance(expr.right, (Constant, Var)):
            lift_expr = LiftExpr(expr.right, operand_dims)
            right_expr = f"decltype({render_expr(expr.right, ctx)})::Simdify({render_expr(lift_expr, ctx)})"
        else:
            right_expr = render_expr(expr.right, ctx)

        # If we're using an arithmetic primitive operation or we're operating on plaintext values,
        # don't cast to a share wrapper
        if ctx.plaintext or expr.operator in (
            BinOpKind.ADD,
            BinOpKind.SUB,
            BinOpKind.MUL,
            BinOpKind.DIV,
            BinOpKind.GT,
        ):
            return f"({left_expr} {expr.operator.value} {right_expr})"

        # Otherwise, convert to a ShareWrapper since they have more operators defined
        # TODO: go through the operators for ShareWrapper and make sure they're all valid
        # for the default protocol
        else:
            return (
                "("
                + (
                    "to_share_wrapper("
                    + left_expr
                    + ")"
                    + " "
                    + _render_operator(expr.operator)
                    + " "
                    + "to_share_wrapper("
                    + right_expr
                    + ")"
                )
                + ")"
            )

    elif isinstance(expr, Constant):
        if ctx.plaintext:
            if expr.datatype == DataType.INT:
                return f"{ctx.int_type}({expr.value})"
            elif expr.datatype == DataType.BOOL:
                return str(expr).lower()
            else:
                raise NotImplementedError(f"Unsupported datatype: {expr.datatype}")

        else:
            return "_MPC_CONSTANT_" + str(expr).lower()

    elif isinstance(expr, DropDim):
        specialization = ""
        # Since we want to manipulate the array, we don't want the input to drop_dim()
        # to be vectorized
        if isinstance(expr.array, VectorizedAccess):
            array = render_expr(expr.array, ctx) + ".Unsimdify()"
            # TODO: move this operation into the vectorization phase
            # Essentially, we may have modified which dimensions are actually getting dropped
            # by lifting this statement out of a loop in phase 2 of vectorization.  The below
            # check makes sure that we're only considering the dimensions which are actually
            # vectorized.
            droppable_dims = tuple(
                dim_size
                for dim_size, vectorized in zip(expr.dims, expr.array.vectorized_dims)
                if vectorized
            )
        else:
            array = render_expr(expr.array, ctx)
            droppable_dims = expr.dims

        if len(droppable_dims) == 1:
            specialization = "_monoreturn"

        dims = (
            "{"
            + ", ".join(
                render_expr(dim_size, dc.replace(ctx, plaintext=True))
                for dim_size in droppable_dims
            )
            + "}"
        )

        return f"drop_dim{specialization}({array}, {dims})"

    elif isinstance(expr, List):
        items = ", ".join(render_expr(item, ctx) for item in expr.items)
        return "{" + items + "}"

    elif isinstance(expr, Mux):
        cpp_cond = render_expr(expr.condition, ctx)
        cond_dims = None
        if isinstance(expr.condition, VectorizedAccess):
            cond_dims = tuple(
                (idx_var, dim_size)
                for idx_var, dim_size, vectorized in zip(
                    expr.condition.idx_vars,
                    expr.condition.dim_sizes,
                    expr.condition.vectorized_dims,
                )
                if vectorized
            )

        if cond_dims and isinstance(expr.true_value, (Constant, Var)):
            lift_expr = LiftExpr(expr.true_value, cond_dims)
            cpp_true_val = f"decltype({render_expr(expr.true_value, ctx)})::Simdify({render_expr(lift_expr, ctx)})"
        else:
            cpp_true_val = render_expr(expr.true_value, ctx)

        if cond_dims and isinstance(expr.false_value, (Constant, Var)):
            lift_expr = LiftExpr(expr.false_value, cond_dims)
            cpp_false_val = f"decltype({render_expr(expr.false_value, ctx)})::Simdify({render_expr(lift_expr, ctx)})"
        else:
            cpp_false_val = render_expr(expr.false_value, ctx)

        return f"{cpp_cond}.Mux({cpp_true_val}.Get(), {cpp_false_val}.Get())"

    elif isinstance(expr, LiftExpr):
        raw_idx_map = lambda idx: f"indices[{idx}]"
        augmented_env = copy(ctx.type_env)
        for idx_var, _dim_size in expr.dims:
            augmented_env[idx_var] = PLAINTEXT_INT
        if (
            not ctx.plaintext
            and type_assign_expr(expr.expr, augmented_env, None, None).is_plaintext()
        ):
            to_shared = (
                lambda val: f"encrypto::motion::SecureUnsignedInteger(party->In<Protocol>(encrypto::motion::ToInput({val}), 0))"
            )

            idx_map = lambda idx: to_shared(raw_idx_map(idx))
        else:
            idx_map = raw_idx_map

        # If we're lifting a vectorized array, don't render a vectorized access or else the lifted array
        # will hold too many values
        expr_to_render = expr.expr
        if isinstance(expr_to_render, VectorizedAccess):
            post_expr = ".Unsimdify()"
        else:
            post_expr = ""

        inner_ctx = dc.replace(
            ctx,
            int_type="std::uint32_t",
            var_mappings={
                var: idx_map(i)
                for i, (var, _) in enumerate(expr.dims)
                if not any(var == loop.counter for loop in ctx.enclosing_loops)
            },
        )
        inner_expr = f"std::function([&](const std::vector<std::uint32_t> &indices){{return {render_expr(expr_to_render, inner_ctx)}{post_expr};}})"

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
        cpp_arr_access = render_expr(Subscript(expr.array, expr.index), ctx)
        cpp_val = render_expr(expr.value, ctx)
        return f"{cpp_arr_access} = {cpp_val}"

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
        dim_sizes = (
            "{"
            + ", ".join(
                render_expr(loop_bound, dc.replace(ctx, plaintext=True))
                for loop_bound, vectorized in zip(expr.dim_sizes, expr.vectorized_dims)
                if vectorized
            )
            + "}"
        )
        vectorized_dims = (
            "{"
            + ", ".join(
                str(vectorized).lower()
                for vectorized in expr.vectorized_dims
                if vectorized
            )
            + "}"
        )
        idxs = "{}"
        update_array = expr.array
        if isinstance(update_array, VectorizedAccess):
            update_array = update_array.array
        return f"vectorized_update({render_expr(update_array, ctx)}, {dim_sizes}, {vectorized_dims}, {idxs}, {render_expr(expr.value, ctx)})"

    return assert_never(expr)
