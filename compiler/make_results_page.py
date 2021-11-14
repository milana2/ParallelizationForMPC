#!/usr/bin/env python3

from argparse import ArgumentParser
import os
import webbrowser
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
        description="Generate a web page with results of the compiler on benchmarks"
    )
    parser.add_argument("--open", action="store_true", help="Open in web browser")
    parser.add_argument("path", help="Directory to store web page")
    args = parser.parse_args()

    html = """
    <html>
        <head>
            <style>
                .table-container {
                    width: 100% !important;
                    overflow-x: scroll;
                }
                table, th, td {
                    border: 1px solid;
                    border-collapse: collapse;
                }
                pre {
                    font-size: 18px;
                }
            </style>
        </head>
        <body>
    """
    for test_case_dir in os.scandir(STAGES_DIR):
        html += f"<h1><pre>{test_case_dir.name}</pre></h1>"
        html += "<div class=table-container> <table>"
        html += """
        <tr>
            <th>Input</th>
            <th>Restricted AST</th>
            <th>Three-address code CFG</th>
            <th>SSA</th>
            <th>SSA ϕ→MUX</th>
            <th>Linear code with loops</th>
        </tr>
        """
        input_path = os.path.join(test_case_dir, "input.py")
        with open(input_path, "r") as f:
            input_text = f.read()
        html += "<tr>"
        html += f"<td><pre>{input_text}</pre></td>"
        ast = python_ast.parse(input_text, filename=input_path)
        restricted_ast = compiler.ast_to_restricted_ast(
            node=ast, filename=input_path, text=input_text
        )
        html += f"<td><pre>{restricted_ast}</pre></td>"
        tac_cfg = compiler.restricted_ast_to_tac_cfg(restricted_ast)
        filename = f"{test_case_dir.name}_tac_cfg.png"
        path = os.path.join(args.path, filename)
        cfg_to_image(tac_cfg.body, path)
        html += f"<td><img src='{filename}'/></td>"
        ssa = compiler.tac_cfg_to_ssa(tac_cfg)
        filename = f"{test_case_dir.name}_ssa.png"
        path = os.path.join(args.path, filename)
        cfg_to_image(ssa.body, path)
        html += f"<td><img src='{filename}'/></td>"
        compiler.replace_phi_with_mux(ssa)
        filename = f"{test_case_dir.name}_ssa_mux.png"
        path = os.path.join(args.path, filename)
        cfg_to_image(ssa.body, path)
        html += f"<td><img src='{filename}'/></td>"
        loop_linear_code = compiler.ssa_to_loop_linear_code(ssa)
        html += f"<td><pre>{loop_linear_code}</pre></td>"
        html += "</tr>"
        html += "</table></div>"
    html += "</body></html>"
    index_html_path = os.path.join(args.path, "index.html")
    with open(index_html_path, "w") as f:
        f.write(html)
    if args.open:
        webbrowser.open(index_html_path)


if __name__ == "__main__":
    main()
