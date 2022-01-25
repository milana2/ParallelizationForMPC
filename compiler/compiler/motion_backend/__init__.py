import io
from jinja2 import Environment, FileSystemLoader
import os
from textwrap import indent
from typing import TypedDict, Union

from ..loop_linear_code import Function, Statement, Phi, Assign, For
from ..type_analysis import TypeEnv, VarVisibility, Constant
from .. import tac_cfg


class OutputParams(TypedDict):
    out_dir: str
    overwrite: bool


def _render_prototype(func: Function, type_env: TypeEnv) -> str:
    return_type = type_env[func.return_value].to_cpp(type_env)
    return (
        f"{return_type} {func.name}(\n"
        + indent("encrypto::motion::PartyPointer &party,\n", "    ")
        + indent(
            ",\n".join(param.to_cpp(type_env) for param in func.parameters), "    "
        )
        + "\n)"
    )


def _render_call(func: Function, type_env: TypeEnv) -> str:
    return (
        f"{func.name}({', '.join(str(param.var.name) for param in func.parameters)});"
    )


def _collect_constants(stmts: list[Statement]) -> list[Constant]:
    def expr_constants(
        expr: Union[tac_cfg.AssignRHS, tac_cfg.SubscriptIndex]
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
        else:
            raise AssertionError(f"Unhandled expression type: {type(expr)}")

    def stmt_constants(stmt: Statement) -> list[Constant]:
        if isinstance(stmt, For):
            return _collect_constants(stmt.body)
        elif isinstance(stmt, Phi):
            return [
                val
                for val in (stmt.rhs_true, stmt.rhs_false)
                if isinstance(val, Constant)
            ]
        else:
            return expr_constants(stmt.rhs)

    return [const for stmt in stmts for const in stmt_constants(stmt)]


def render_function(func: Function, type_env: TypeEnv) -> str:
    func_header = f"{_render_prototype(func, type_env)} {{"

    var_definitions = (
        "// Shared variable declarations\n"
        + "\n".join(
            var_type.to_cpp(type_env, plaintext=False)
            + " "
            + var_name.to_cpp(type_env)
            + ";"
            for var_name, var_type in type_env.items()
        )
        + "\n"
    )

    plaintext_var_definitions = (
        "// Plaintext variable declarations\n"
        + "\n".join(
            f"{var_type.to_cpp(type_env, plaintext=True)} {var.to_cpp(type_env, plaintext=True)};"
            for var, var_type in type_env.items()
            if var_type.is_plaintext()
        )
        + "\n"
    )

    plaintext_constants = set(_collect_constants(func.body))
    constant_initialization = (
        "// Constant initializations\n"
        + "\n".join(
            f"{const.datatype.to_cpp(type_env, plaintext=False)} {const.to_cpp(type_env)} = "
            + f"encrypto::motion::proto::ConstantBooleanInputGate(encrypto::motion::ToInput({const.to_cpp(type_env, plaintext=True)}), *party->GetBackend()).GetOutputAsShare();"
            for const in plaintext_constants
        )
        + "\n"
    )

    param_assignments = (
        "// Shared parameter assignments\n"
        + "\n".join(
            param.var.to_cpp(type_env) + "_0 = " + param.var.to_cpp(type_env) + ";"
            for param in func.parameters
            if param.var_type.is_shared()
        )
        + "\n"
    )

    plaintext_param_assignments = (
        "// Plaintext parameter assignments\n"
        + "\n\n".join(
            (
                # Initialize the shared version
                param.var.to_cpp(type_env)
                + "_0 = encrypto::motion::proto::ConstantBooleanInputGate(encrypto::motion::ToInput("
                + param.var.to_cpp(
                    type_env
                )  # no plaintext=True here so we reference the right variable name
                + "), *party->GetBackend()).GetOutputAsShare();"
            )
            + "\n"
            + (
                # Initialize the plaintext version
                param.var.to_cpp(type_env, plaintext=True)
                + "_0 = "
                + param.var.to_cpp(type_env)
                + ";"
            )
            for param in func.parameters
            if param.var_type.is_plaintext()
        )
        + "\n"
    )

    func_body = (
        "// Function body\n"
        + "\n".join(
            stmt.to_cpp(type_env) for stmt in func.body if not isinstance(stmt, Phi)
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
        + indent(param_assignments, "    ")
        + "\n"
        + indent(plaintext_param_assignments, "    ")
        + "\n"
        + indent(func_body, "    ")
        + "\n"
        + indent(f"return {func.return_value.to_cpp(type_env)};", "    ")
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

    rendered_main = main_template.render(
        header_fname=f"{func.name}.h",
        params=[
            {
                "name": param.var.name,
                "cpp_type": param.var_type.to_cpp(type_env),
                "plaintext_cpp_type": param.var_type.to_cpp(type_env, plaintext=True),
                "is_shared": param.var_type.visibility == VarVisibility.SHARED,
                "dims": param.var_type.dims,
                "party_idx": param.party_idx,
                "default_value": param.default_values[0]
                if len(param.default_values) > 0
                else None,
            }
            for param in func.parameters
        ],
        protocol="encrypto::motion::MpcProtocol::kBmr",  # TODO: make this user-configurable
        num_returns=type_env[func.return_value].dims,
        return_type=type_env[func.return_value].to_cpp(type_env),
        function_name=func.name,
    )

    rendered_header = header_template.render(
        circuit_generator=render_function(func, type_env),
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
