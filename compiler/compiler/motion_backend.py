import io
from textwrap import indent

from .loop_linear_code import Function, Statement, Phi
from .type_analysis import TypeEnv


def render_function(func: Function, type_env: TypeEnv) -> str:
    return_type = type_env[func.return_value].to_cpp()
    func_header = (
        "template <encrypto::motion::MpcProtocol Protocol>\n"
        + f"{return_type} {func.name}(\n"
        + indent("encrypto::motion::PartyPointer &party,\n", "    ")
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

    # TODO: once parameter renaming is properly implemented, this shouldn't be necessary
    param_assignments = (
        "// Parameter assignments\n"
        + "\n".join(
            param.var.to_cpp() + "_0 = " + param.var.to_cpp() + ";"
            for param in func.parameters
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
        + indent(param_assignments, "    ")
        + "\n"
        + indent(func_body, "    ")
        + indent(f"return {func.return_value.to_cpp()};", "    ")
        + "\n}"
    )
