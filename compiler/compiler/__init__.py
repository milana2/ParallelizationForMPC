import ast
import sys
import traceback
from typing import Optional

from .ast_to_restricted_ast import ast_to_restricted_ast
from .restricted_ast_to_tac_cfg import restricted_ast_to_tac_cfg
from .tac_cfg_to_ssa import tac_cfg_to_ssa
from .ssa_phi_to_mux import replace_phi_with_mux
from .dead_code_elim import dead_code_elim
from .ssa_to_loop_linear_code import ssa_to_loop_linear_code
from .dep_graph import DepGraph
from .type_analysis import type_check
from . import loop_linear_code
from . import motion_backend
from . import vectorize


def compile(
    filename: str,
    text: str,
    quiet: bool = True,
    run_vectorization: bool = True,
    out_dir: Optional[str] = None,
    overwrite_out_dir: bool = False,
    protocol: Optional[str] = None,
):
    try:
        ast_module = ast.parse(text, filename=filename)
        ast_node = ast_to_restricted_ast(node=ast_module, filename=filename, text=text)
    except SyntaxError as err:
        traceback.print_exception(None, value=err, tb=None)
        sys.exit(1)

    if not quiet:
        print("Restricted AST:")
        print(ast_node)
        print()

    tac = restricted_ast_to_tac_cfg(ast_node)
    if not quiet:
        print("Three-address code control flow graph:")
        print(tac)
        print()

    ssa = tac_cfg_to_ssa(tac)
    if not quiet:
        print("Static single assignment form:")
        print(ssa)
        print()

    replace_phi_with_mux(ssa)
    if not quiet:
        print("MUX static single assignment form:")
        print(ssa)
        print()

    dead_code_elim(ssa)
    if not quiet:
        print("Dead code elimination:")
        print(ssa)
        print()

    linear = ssa_to_loop_linear_code(ssa)
    if not quiet:
        print("Linear code with loops:")
        print(linear)
        print()

    dep_graph = DepGraph(linear)
    if not quiet:
        print("Dependence graph:")
        print(dep_graph)
        print()

    vectorize.remove_infeasible_edges(linear, dep_graph)
    if not quiet:
        print("Dependence graph after removal of infeasible edges:")
        print(dep_graph)
        print()

    (linear, dep_graph) = vectorize.refine_array_mux(linear, dep_graph)
    if not quiet:
        print("Array MUX refinement:")
        print(linear)
        print()
        print("Array MUX refinement (dependence graph):")
        print(dep_graph)
        print()

    if run_vectorization:
        (linear, dep_graph) = vectorize.basic_vectorization_phase_1(linear, dep_graph)
        if not quiet:
            print("Basic Vectorization phase 1 (no typing):")
            print(linear)
            print()

    (linear, type_env) = type_check(linear, dep_graph)
    if not quiet:
        print("Type environment after basic vectorization phase 1:")
        print(type_env)
        print()

        print("Basic Vectorization phase 1 (with vectorized array knowledge):")
        print(linear)
        print()

    if run_vectorization:
        (linear, type_env, dep_graph) = vectorize.basic_vectorization_phase_2(
            linear, type_env, dep_graph
        )
        if not quiet:
            print("Type environment after basic vectorization phase 2:")
            print(type_env)
            print()

            print("Basic Vectorization phase 2:")
            print(linear)
            print()

    motion_code = motion_backend.render_function(linear, type_env)
    if not quiet:
        print("Motion code:")
        print(motion_code)
        print()

    if out_dir:
        if protocol not in motion_backend.VALID_PROTOCOLS:
            raise ValueError(
                "Invalid protocol: {}. Valid protocols are: {}".format(
                    protocol, motion_backend.VALID_PROTOCOLS
                )
            )

        motion_backend.render_application(
            linear,
            type_env,
            {"out_dir": out_dir, "overwrite": overwrite_out_dir, "protocol": protocol},
        )
