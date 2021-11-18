#!/usr/bin/env python3

from argparse import ArgumentParser
import os
import ast as python_ast

import networkx
import pydot

import compiler
import compiler.loop_linear_code as llc
from compiler.util import assert_never
from tests import STAGES_DIR


def cfg_to_image(G: networkx.DiGraph, path: str):
    """Write a PNG image of the control flow graph in `G` to `path`."""
    # The node labels must be unique for pydot to consider nodes to be separate
    G = networkx.convert_node_labels_to_integers(G, label_attribute="label")
    G.graph["node"] = {"shape": "box", "fontname": "monospace"}
    dot = networkx.nx_pydot.to_pydot(G)
    dot.write(path, format="png")


def dep_graph_to_image(
    dep_graph: compiler.dep_graph.DepGraph, function: llc.Function, path: str
):
    dot = pydot.Dot()
    dot.set_graph_defaults(rankdir="LR")
    dot.set_node_defaults(fontname="monospace")

    statement_ints: dict[llc.Statement, int] = dict()

    def search(statements: list[llc.Statement], i: int = 0) -> str:
        result: list[str] = []

        for statement in statements:
            i += 1
            statement_ints[statement] = i
            if isinstance(statement, llc.Phi) or isinstance(statement, llc.Assign):
                s = str(statement).replace("<", r"\<").replace(">", r"\>")
                result.append(f"<{i}> [{i}] {s}")
            elif isinstance(statement, llc.For):
                result.append(
                    f"<{i}> {statement.heading_str()} | {{ | {{ {search(statement.body, i)} }} }}"
                )
            else:
                assert_never(statement)

        return " | ".join(result)

    dot.add_node(
        pydot.Node(
            name="main_node",
            label=search(function.body),
            shape="record",
        )
    )

    for var_def, var_uses in dep_graph.items():
        for var_use in var_uses:
            dot.add_edge(
                pydot.Edge(src=statement_ints[var_def], dst=statement_ints[var_use])
            )

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

        dep_graph = compiler.compute_dep_graph(loop_linear_code)
        filename = f"{test_case_dir.name}_dep_graph.png"
        path = os.path.join(args.path, filename)
        dep_graph_to_image(dep_graph, loop_linear_code, path)
        md += "### Dependency graph\n"
        md += f"![]({filename})\n"

    md_path = os.path.join(args.path, "README.md")
    with open(md_path, "w") as f:
        f.write(md)


if __name__ == "__main__":
    main()
