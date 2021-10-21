#!/usr/bin/env python3

import argparse
import ast

from ast_to_restricted_ast import ast_to_restricted_ast
from restricted_ast_to_tac_cfg import restricted_ast_to_tac_cfg


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=argparse.FileType("r"))
    return parser.parse_args()


def main():
    args = parse_args()
    ast_node = ast.parse(args.input.read())
    ast_node = ast_to_restricted_ast(ast_node)
    cfg = restricted_ast_to_tac_cfg(ast_node)

    print("\n".join([str(n) for n in cfg.body.nodes]))


if __name__ == "__main__":
    main()
