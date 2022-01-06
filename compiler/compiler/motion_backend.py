import io
from textwrap import indent

from .loop_linear_code import Function, Statement, Phi
from .type_analysis import TypeEnv


def render_function(func: Function, type_env: TypeEnv) -> str:
    return_type = "void"
    # TODO: uncomment this when typing is fixed - return_type = type_env[func.return_value].to_cpp()
    func_header = (
        f"{return_type} {func.name}(\n"
        + indent(",\n".join(param.to_cpp() for param in func.parameters), "    ")
        + "\n) {"
    )

    var_definitions = (
        "// Initial variable declarations\n"
        + "\n".join(
            var_type.to_cpp() + " " + var_name.to_cpp() + ";"
            for var_name, var_type in type_env.items()
        )
        + "\n"
    )

    func_body = (
        "// Function body\n"
        + "\n".join(stmt.to_cpp() for stmt in func.body if not isinstance(stmt, Phi))
        + "\n"
    )

    return (
        func_header
        + "\n"
        + indent(var_definitions, "    ")
        + "\n"
        + indent(func_body, "    ")
        + indent(f"return {func.return_value.to_cpp()};", "    ")
        + "\n}"
    )
