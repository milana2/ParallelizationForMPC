#!/usr/bin/env python3

import argparse
import ast

from ast_to_restricted_ast import ast_to_restricted_ast
from restricted_ast_to_tac_cfg import restricted_ast_to_tac_cfg
from tac_cfg_to_ssa import tac_cfg_to_ssa


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=argparse.FileType("r"))
    return parser.parse_args()


def main():
    args = parse_args()
    ast_node = ast.parse(args.input.read())
    ast_node = ast_to_restricted_ast(ast_node)
    tac = restricted_ast_to_tac_cfg(ast_node)
    ssa = tac_cfg_to_ssa(tac)

    print("\n".join([str(n) for n in ssa.body.nodes]))


if __name__ == "__main__":
    main()
