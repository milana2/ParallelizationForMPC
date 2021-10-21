#!/usr/bin/env python3

import argparse
import ast

from ast_to_restricted_ast import ast_to_restricted_ast


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=argparse.FileType("r"))
    return parser.parse_args()


def main():
    args = parse_args()
    ast_node = ast.parse(args.input.read())
    ast_node = ast_to_restricted_ast(ast_node)

    print(ast_node)


if __name__ == "__main__":
    main()
