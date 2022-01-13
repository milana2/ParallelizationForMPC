import io
from jinja2 import Environment, FileSystemLoader
import os
from textwrap import indent
from argparse import Namespace

from ..loop_linear_code import Function, Statement, Phi
from ..type_analysis import TypeEnv, VarVisibility


def _render_prototype(func: Function, type_env: TypeEnv) -> str:
    return_type = type_env[func.return_value].to_cpp()
    return (
        "template <encrypto::motion::MpcProtocol Protocol>\n"
        + f"{return_type} {func.name}(\n"
        + indent("encrypto::motion::PartyPointer &party,\n", "    ")
        + indent(",\n".join(param.to_cpp() for param in func.parameters), "    ")
        + "\n)"
    )


def _render_call(func: Function, type_env: TypeEnv) -> str:
    return f"{func.name}<Protocol>({', '.join(str(param.var.name) for param in func.parameters)});"


def render_function(func: Function, type_env: TypeEnv) -> str:
    func_header = f"{_render_prototype(func, type_env)} {{"

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


def render_application(func: Function, type_env: TypeEnv, args: Namespace):
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
                "cpp_type": param.var_type.to_cpp(),
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
        return_type=type_env[func.return_value].to_cpp(),
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

    output_dir = os.path.abspath(args.out_dir)

    os.makedirs(output_dir, exist_ok=args.overwrite)

    with open(os.path.join(output_dir, f"main.cpp"), "w") as main_file:
        main_file.write(rendered_main)

    with open(os.path.join(output_dir, f"{func.name}.h"), "w") as header_file:
        header_file.write(rendered_header)

    with open(os.path.join(output_dir, "CMakeLists.txt"), "w") as cmakelists_file:
        cmakelists_file.write(rendered_cmakelists)
