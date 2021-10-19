#!/usr/bin/env python3

import argparse
import ast

from ast_to_tac import ast_to_tac


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=argparse.FileType("r"))
    return parser.parse_args()


def main():
    args = parse_args()
    ast_node = ast.parse(args.input.read())
    tac_node = ast_to_tac(ast_node)

    print(tac_node)


if __name__ == "__main__":
    main()
