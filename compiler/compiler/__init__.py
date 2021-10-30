import argparse
import ast

from .ast_to_restricted_ast import ast_to_restricted_ast
from .restricted_ast_to_tac_cfg import restricted_ast_to_tac_cfg
from .tac_cfg_to_ssa import tac_cfg_to_ssa
from .ssa_phi_to_mux import replace_phi_with_mux


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=argparse.FileType("r"))
    return parser.parse_args()


def main():
    args = parse_args()
    ast_node = ast.parse(args.input.read())

    ast_node = ast_to_restricted_ast(ast_node)
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
