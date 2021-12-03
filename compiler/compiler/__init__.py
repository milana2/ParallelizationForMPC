import argparse
import ast
import sys
import traceback

from .ast_to_restricted_ast import ast_to_restricted_ast
from .restricted_ast_to_tac_cfg import restricted_ast_to_tac_cfg
from .tac_cfg_to_ssa import tac_cfg_to_ssa
from .ssa_phi_to_mux import replace_phi_with_mux
from .dead_code_elim import dead_code_elim
from .ssa_to_loop_linear_code import ssa_to_loop_linear_code
from .dep_graph import compute_dep_graph
from . import loop_linear_code
from . import vectorize


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=argparse.FileType("r"))
    return parser.parse_args()


def main():
    args = parse_args()
    filename = args.input.name
    text = args.input.read()

    try:
        ast_node = ast.parse(text, filename=filename)
        ast_node = ast_to_restricted_ast(node=ast_node, filename=filename, text=text)
    except SyntaxError as err:
        traceback.print_exception(etype=None, value=err, tb=None)
        sys.exit(1)

    print("Restricted AST:")
    print(ast_node)
    print()

    tac = restricted_ast_to_tac_cfg(ast_node)
    print("Three-address code control flow graph:")
    print(tac)
    print()

    ssa = tac_cfg_to_ssa(tac)
    print("Static single assignment form:")
    print(ssa)
    print()

    replace_phi_with_mux(ssa)
    print("MUX static single assignment form:")
    print(ssa)
    print()

    dead_code_elim(ssa)
    print("Dead code elimination:")
    print(ssa)
    print()

    linear = ssa_to_loop_linear_code(ssa)
    print("Linear code with loops:")
    print(linear)
    print()

    dep_graph = compute_dep_graph(linear)
    print("Dependence graph:")
    for var_def, var_uses in dep_graph.items():
        print(var_def)
        for var_use in var_uses:
            print(f"    {var_use}")
    print()
