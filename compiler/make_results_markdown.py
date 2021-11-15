#!/usr/bin/env python3

from argparse import ArgumentParser
import os
import ast as python_ast

import networkx

import compiler
from tests import STAGES_DIR


def cfg_to_image(G: networkx.DiGraph, path: str):
    """Write a PNG image of the control flow graph in `G` to `path`."""
    # The node labels must be unique for pydot to consider nodes to be separate
    G = networkx.convert_node_labels_to_integers(G, label_attribute="label")
    G.graph["node"] = {"shape": "box", "fontname": "monospace"}
    dot = networkx.nx_pydot.to_pydot(G)
    dot.write(path, format="png")


def main():
    parser = ArgumentParser(
        description="Generate a markdown file with results of the compiler on benchmarks"
    )
    parser.add_argument("path", help="Directory to store files")
    args = parser.parse_args()

    try:
        os.mkdir(args.path)
    except FileExistsError:
        pass

    md = "# Compiler stages with different benchmarks\n"
    for test_case_dir in sorted(os.scandir(STAGES_DIR), key=lambda entry: entry.name):
        md += f"## `{test_case_dir.name}`\n"
        input_path = os.path.join(test_case_dir, "input.py")
        with open(input_path, "r") as f:
            input_text = f.read()
        md += "### Input\n"
        md += f"```python\n{input_text}\n```\n"
        ast = python_ast.parse(input_text, filename=input_path)
        restricted_ast = compiler.ast_to_restricted_ast(
            node=ast, filename=input_path, text=input_text
        )
        md += "### Restricted AST\n"
        md += f"```python\n{restricted_ast}\n```\n"
        tac_cfg = compiler.restricted_ast_to_tac_cfg(restricted_ast)
        filename = f"{test_case_dir.name}_tac_cfg.png"
        path = os.path.join(args.path, filename)
        cfg_to_image(tac_cfg.body, path)
        md += "### Three-address code CFG\n"
        md += f"![]({filename})\n"
        ssa = compiler.tac_cfg_to_ssa(tac_cfg)
        filename = f"{test_case_dir.name}_ssa.png"
        path = os.path.join(args.path, filename)
        cfg_to_image(ssa.body, path)
        md += "### SSA\n"
        md += f"![]({filename})\n"
        compiler.replace_phi_with_mux(ssa)
        filename = f"{test_case_dir.name}_ssa_mux.png"
        path = os.path.join(args.path, filename)
        cfg_to_image(ssa.body, path)
        md += "### SSA ϕ→MUX\n"
        md += f"![]({filename})\n"
        loop_linear_code = compiler.ssa_to_loop_linear_code(ssa)
        md += "### Linear code with loops\n"
        md += f"```python\n{loop_linear_code}\n```\n"
    md_path = os.path.join(args.path, "README.md")
    with open(md_path, "w") as f:
        f.write(md)


if __name__ == "__main__":
    main()
