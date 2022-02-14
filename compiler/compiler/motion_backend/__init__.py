import dataclasses as dt
import io
from jinja2 import Environment, FileSystemLoader # type: ignore
import os
from textwrap import indent
from typing import TypedDict, Union

from compiler.ast_shared import DropDim, RaiseDim, VectorizedArr

from ..util import assert_never
from ..loop_linear_code import Function, Statement, Phi, Assign, For
from ..type_analysis import TypeEnv, VarVisibility, Constant, DataType
from .. import tac_cfg

from .low_level_rendering import (
    RenderContext,
    render_datatype,
    render_expr,
    render_param,
    render_stmt,
    render_type,
)


class OutputParams(TypedDict):
    out_dir: str
    overwrite: bool


def _render_prototype(func: Function, type_env: TypeEnv) -> str:
    return_type = render_type(type_env[func.return_value], plaintext=False)
    return (
        f"template <encrypto::motion::MpcProtocol Protocol>\n"
        f"{return_type} {func.name}(\n"
        + indent("encrypto::motion::PartyPointer &party,\n", "    ")
        + indent(
            ",\n".join(render_param(param, type_env) for param in func.parameters),
            "    ",
        )
        + "\n)"
    )


def _render_call(func: Function, type_env: TypeEnv) -> str:
    return (
        f"{func.name}({', '.join(str(param.var.name) for param in func.parameters)});"
    )


def _collect_constants(stmts: list[Statement]) -> list[Constant]:
    def expr_constants(
        expr: Union[tac_cfg.AssignRHS, tac_cfg.SubscriptIndex, RaiseDim, DropDim, VectorizedArr]
    ) -> list[Constant]:
        if isinstance(expr, Constant):
            return [expr]
        elif isinstance(expr, (tac_cfg.Var, tac_cfg.Subscript)):
            return []
        elif isinstance(expr, tac_cfg.BinOp):
            return [*expr_constants(expr.left), *expr_constants(expr.right)]
        elif isinstance(expr, tac_cfg.UnaryOp):
            return expr_constants(expr.operand)
        elif isinstance(expr, tac_cfg.List):
            return [const for val in expr.items for const in expr_constants(val)]
        elif isinstance(expr, tac_cfg.Tuple):
            # TODO: Figure out the best way to handle constants here
            return [const for val in expr.items for const in expr_constants(val)]
        elif isinstance(expr, tac_cfg.Mux):
            return [
                val
                for val in (expr.true_value, expr.false_value)
                if isinstance(val, Constant)
            ]
        elif isinstance(expr, tac_cfg.Update):
            return [*expr_constants(expr.index), *expr_constants(expr.value)]
        elif isinstance(expr, RaiseDim):
            return [
                const
                for _, dim_bound in expr.dims
                for const in expr_constants(dim_bound)
            ]
        elif isinstance(expr, DropDim):
            return [
                const for dim_bound in expr.dims for const in expr_constants(dim_bound)
            ]
        else:
            raise AssertionError(f"Unhandled expression type: {type(expr)}")

    def stmt_constants(stmt: Statement) -> list[Constant]:
        if isinstance(stmt, For):
            return _collect_constants(stmt.body)
        elif isinstance(stmt, Assign):
            return expr_constants(stmt.rhs)
        elif isinstance(stmt, (Phi, RaiseDim, DropDim)):
            return []
        else:
            assert_never(stmt)

    return [const for stmt in stmts for const in stmt_constants(stmt)]


def render_function(func: Function, type_env: TypeEnv) -> str:
    render_ctx = RenderContext(type_env)

    func_header = f"{_render_prototype(func, type_env)} {{"

    var_definitions = (
        "// Shared variable declarations\n"
        + "\n".join(
            render_type(var_type, plaintext=False)
            + " "
            + render_expr(var, dt.replace(render_ctx, plaintext=False))
            + ";"
            for var, var_type in sorted(type_env.items(), key=lambda x: str(x[0]))
            if not any(
                param.var == var and param.var_type.is_shared()
                for param in func.parameters
            )
        )
        + "\n"
    )

    plaintext_var_definitions = (
        "// Plaintext variable declarations\n"
        + "\n".join(
            f"{render_type(var_type, plaintext=True)} {render_expr(var, dt.replace(render_ctx, plaintext=True))};"
            for var, var_type in sorted(type_env.items(), key=lambda x: str(x[0]))
            if var_type.is_plaintext()
            if not any(
                param.var == var and param.var_type.is_plaintext()
                for param in func.parameters
            )
        )
        + "\n"
    )

    plaintext_constants = set(_collect_constants(func.body))
    constant_initialization = (
        "// Constant initializations\n"
        + "\n".join(
            f"{render_datatype(const.datatype, plaintext=False)} {render_expr(const, render_ctx)} = "
            + f"party->In<Protocol>({render_expr(const, dt.replace(render_ctx, as_motion_input=True))}, 0);"
            for const in sorted(plaintext_constants, key=lambda c: str(c.value))
        )
        + "\n"
    )

    plaintext_param_assignments = (
        "// Plaintext parameter assignments\n"
        + "\n\n".join(
            (
                # Initialize the shared version
                render_expr(param.var, render_ctx)
                + " = party->In<Protocol>(encrypto::motion::ToInput("
                + render_expr(param.var, dt.replace(render_ctx, plaintext=True))
                + "), 0);"
            )
            for param in sorted(func.parameters, key=str)
            if param.var_type.is_plaintext()
        )
        + "\n"
    )

    func_body = (
        "// Function body\n"
        + "\n".join(
            render_stmt(stmt, type_env)
            for stmt in func.body
            if not isinstance(stmt, Phi)
        )
        + "\n"
    )

    return (
        func_header
        + "\n"
        + indent(var_definitions, "    ")
        + "\n"
        + indent(plaintext_var_definitions, "    ")
        + "\n"
        + indent(constant_initialization, "    ")
        + "\n"
        + indent(plaintext_param_assignments, "    ")
        + "\n"
        + indent(func_body, "    ")
        + "\n"
        + indent(f"return {render_expr(func.return_value, render_ctx)};", "    ")
        + "\n}"
    )


def render_application(func: Function, type_env: TypeEnv, params: OutputParams) -> None:
    template_dir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.abspath(os.path.join(template_dir, "..", "..", ".."))

    template_loader = FileSystemLoader(os.path.abspath(os.path.dirname(__file__)))
    template_env = Environment(loader=template_loader)

    main_template = template_env.get_template("main.cpp.jinja")
    header_template = template_env.get_template("header.h.jinja")
    cpp_template = template_env.get_template("circuit_gen.cpp.jinja")
    cmakelists_template = template_env.get_template("CMakeLists.txt.jinja")

    return_type = type_env[func.return_value]

    rendered_main = main_template.render(
        header_fname=f"{func.name}.h",
        params=[
            {
                "name": param.var.name,
                "cpp_type": render_type(
                    param.var_type, plaintext=type_env[param.var].is_plaintext()
                ),
                "plaintext_cpp_type": render_type(param.var_type, plaintext=True),
                "is_shared": param.var_type.visibility == VarVisibility.SHARED,
                "dims": param.var_type.dims,
                "party_idx": param.party_idx,
                "default_value": param.default_values[0]
                if len(param.default_values) > 0
                else None,
            }
            for param in func.parameters
        ],
        protocol="encrypto::motion::MpcProtocol::kBooleanGmw",  # TODO: make this user-configurable
        num_returns=type_env[func.return_value].dims,
        outputs=[render_type(return_type, plaintext=True)]
        if return_type.datatype != DataType.TUPLE
        else [render_type(t, plaintext=True) for t in return_type.tuple_types],
        function_name=func.name,
    )

    rendered_header = header_template.render(
        circuit_generator=render_function(func, type_env)
    )

    rendered_cmakelists = cmakelists_template.render(
        app_name=func.name,
        motion_dir=os.path.join(project_root, "MOTION"),
        cpp_files=["main.cpp"],
    )

    output_dir = os.path.abspath(params["out_dir"])

    os.makedirs(output_dir, exist_ok=params["overwrite"])

    with open(os.path.join(output_dir, f"main.cpp"), "w") as main_file:
        main_file.write(rendered_main)

    with open(os.path.join(output_dir, f"{func.name}.h"), "w") as header_file:
        header_file.write(rendered_header)

    with open(os.path.join(output_dir, "CMakeLists.txt"), "w") as cmakelists_file:
        cmakelists_file.write(rendered_cmakelists)
