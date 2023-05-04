#!/usr/bin/env python3

from argparse import ArgumentParser
import os
import ast as python_ast

import networkx
import pydot

import compiler
import compiler.loop_linear_code as llc
import compiler.backends
from compiler.type_analysis import TypeEnv
from compiler.util import assert_never
from tests.context import STAGES_DIR, SKIPPED_TESTS
from tests.backends.motion.benchmark import run_benchmark as motion_run_benchmark
from tests.backends.mp_spdz.benchmark import (
    run_benchmark as spdz_run_benchmark,
    get_compile_stats_arith as spdz_get_compile_stats_arith,
    get_compile_stats_bin as spdz_get_compile_stats_bin,
)
from tests.backends import Backend


def cfg_to_image(G: networkx.DiGraph, path: str):
    """Write a PNG image of the control flow graph in `G` to `path`."""

    # The node labels must be unique for pydot to consider nodes to be separate
    G = networkx.convert_node_labels_to_integers(G, label_attribute="label")

    # Avoid this error in nx_pydot:
    #     ValueError: Node names and attributes should not contain ":" unless they are quoted with "".
    #     For example the string 'attribute:data1' should be written as '"attribute:data1"'.
    #     Please refer https://github.com/pydot/pydot/issues/258
    for node in G.nodes:
        G.nodes[node]["label"] = f'"{G.nodes[node]["label"]}"'

    for edge in G.edges:
        # Avoid this error in nx_pydot:
        #     TypeError: argument of type 'BranchKind' is not iterable
        G.edges[edge]["label"] = str(G.edges[edge]["label"])

        # Avoid this error in nx_pydot:
        #     TypeError: argument of type 'int' is not iterable
        del G.edges[edge]["ident"]

    G.graph["node"] = {"shape": "box", "fontname": "monospace"}
    dot = networkx.nx_pydot.to_pydot(G)
    dot.write(path, format="png")


def dep_graph_to_image(
    dep_graph: compiler.dep_graph.DepGraph, function: llc.Function, path: str
):
    dot = pydot.Dot()
    dot.set_node_defaults(fontname="monospace")

    def search(
        statements: list[llc.Statement], indent: int
    ) -> list[tuple[int, llc.Statement]]:
        result: list[tuple[int, llc.Statement]] = []

        for statement in statements:
            result.append((indent, statement))
            if isinstance(statement, (llc.Phi, llc.Assign, llc.Return)):
                pass
            elif isinstance(statement, llc.For):
                result += search(statement.body, indent + 1)
            else:
                assert_never(statement)

        return result

    all_statements = search(function.body, 0)

    main_label = ""
    for i, (indent, statement) in enumerate(all_statements):
        if isinstance(statement, (llc.Phi, llc.Assign, llc.Return)):
            s = str(statement)
        elif isinstance(statement, llc.For):
            s = statement.heading_str()
        else:
            assert_never(statement)
        num = str(i).rjust(3)
        indent = "    " * indent
        main_label += rf"{num} {indent}{s}\l"

    dot.add_node(pydot.Node(name="main_node", label=main_label, shape="box"))

    statement_indices: dict[llc.Statement, int] = {
        statement: i for i, (_, statement) in enumerate(all_statements)
    }

    for var_def, var_use in dep_graph.edges():
        if isinstance(var_def, compiler.dep_graph.DepParameter) or isinstance(
            var_use, compiler.dep_graph.DepParameter
        ):
            continue

        def_index = statement_indices[var_def]
        use_index = statement_indices[var_use]
        style = "dashed" if dep_graph.is_back_edge(var_def, var_use) else "solid"
        dot.add_edge(pydot.Edge(src=def_index, dst=use_index, style=style))

    dot.write(path, format="png")


def type_env_to_table(type_env: TypeEnv) -> str:
    return (
        "| Variable | Type |\n"
        + "| - | - |\n"
        + "\n".join(
            [f"| `{var}` | `{var_type}` |" for var, var_type in type_env.items()]
        )
    )


def build_motion_benchmark_tables(circuits_path: str) -> str:
    table = "## MOTION Benchmark Data\n"
    for protocol in compiler.backends.motion.VALID_PROTOCOLS:
        table += f"\n### {protocol}\n"

        table += "| Benchmark | Total # Gates | # SIMD gates | # Non-SIMD gates | # messages sent (party 0) | Sent size (party 0) | # messages received (party 0) | Received Size (party 0) | Runtime | Circuit Generation Time |\n"
        table += "| - | - | - | - | - | - | - | - | - | - |\n"

        for test_case_dir in sorted(
            os.scandir(STAGES_DIR), key=lambda entry: entry.name
        ):
            if test_case_dir.name in (
                SKIPPED_TESTS[None] + SKIPPED_TESTS[Backend.MOTION]
            ):
                continue

            for vectorized in (True, False):
                try:
                    maybe_data = motion_run_benchmark(
                        test_case_dir.name, test_case_dir.path, protocol, vectorized
                    )
                    assert maybe_data is not None
                    data, _ = maybe_data
                except Exception as e:
                    print(
                        f"Skipping {test_case_dir.name} (vectorized={vectorized}) due to error: {e}"
                    )
                    continue

                table += "|"
                table += (
                    test_case_dir.name
                    + (" (Non-Vectorized)" if not vectorized else "")
                    + "|"
                )
                table += str(data.circuit_stats.num_gates) + "|"
                table += str(data.circuit_stats.num_simd_gates) + "|"
                table += str(data.circuit_stats.num_nonsimd_gates) + "|"
                table += str(data.timing_stats.communication.send_num_msgs) + "|"
                table += str(data.timing_stats.communication.send_size) + " MiB |"
                table += str(data.timing_stats.communication.recv_num_msgs) + "|"
                table += str(data.timing_stats.communication.recv_size) + " MiB |"
                table += str(data.timing_stats.gates_online.mean) + " ms |"
                table += str(data.circuit_stats.circuit_gen_time) + " ms |\n"

    return table


def build_spdz_benchmark_tables() -> str:
    table = "## MP-SPDZ Benchmark Data\n"

    test_case_dirs = [
        test_case_dir
        for test_case_dir in sorted(
            os.scandir(STAGES_DIR), key=lambda entry: entry.name
        )
        if test_case_dir.name
        not in SKIPPED_TESTS[None] + SKIPPED_TESTS[Backend.MP_SPDZ]
    ]

    table += "### Arithmetic protocol compilation\n"
    table += "| Benchmark | Compile time (seconds) | # int triples | # int opens | # VM rounds |\n"
    table += "| - | - | - | - | - |\n"
    for test_case_dir in test_case_dirs:
        for vectorized in (True, False):
            data = spdz_get_compile_stats_arith(
                test_case_dir.name, test_case_dir.path, vectorized
            )
            table += "|"
            table += (
                test_case_dir.name
                + (" (Non-Vectorized)" if not vectorized else "")
                + "|"
            )
            table += str(round(data.time, ndigits=3)) + "|"
            table += str(data.int_triples) + "|"
            table += str(data.int_opens) + "|"
            table += str(data.vm_rounds) + "|"
            table += "\n"

    binary = 32
    table += f"### Binary protocol compilation ({binary} bit default)\n"
    table += "| Benchmark | Compile time (seconds) | # bit triples | # VM rounds |\n"
    table += "| - | - | - | - |\n"
    for test_case_dir in test_case_dirs:
        for vectorized in (True, False):
            data = spdz_get_compile_stats_bin(
                test_case_dir.name, test_case_dir.path, vectorized, binary
            )
            table += "|"
            table += (
                test_case_dir.name
                + (" (Non-Vectorized)" if not vectorized else "")
                + "|"
            )
            table += str(round(data.time, ndigits=3)) + "|"
            table += str(data.bit_triples) + "|"
            table += str(data.vm_rounds) + "|"
            table += "\n"

    for protocol in compiler.backends.mp_spdz.VALID_PROTOCOLS:
        table += f"\n### {protocol.title()} protocol\n"

        table += "| Benchmark | Time (seconds) | Data sent (MB) |\n"
        table += "| - | - | - |\n"

        for test_case_dir in test_case_dirs:
            for vectorized in (True, False):
                data = spdz_run_benchmark(
                    test_case_dir.name, test_case_dir.path, protocol, vectorized
                )

                table += "|"
                table += (
                    test_case_dir.name
                    + (" (Non-Vectorized)" if not vectorized else "")
                    + "|"
                )
                table += str(data.time_seconds) + "|"
                table += str(data.data_sent_mb) + "|"
                table += "\n"

    return table


def main():
    parser = ArgumentParser(
        description="Generate a markdown file with results of the compiler on benchmarks"
    )
    parser.add_argument("path", help="Directory to store files")
    args = parser.parse_args()

    os.makedirs(os.path.join(args.path, "images"), exist_ok=True)
    circuits_path = os.path.join(args.path, "circuits")
    os.makedirs(circuits_path, exist_ok=True)

    md = "# Compiler results data\n"

    md += build_motion_benchmark_tables(circuits_path) + "\n"
    md += build_spdz_benchmark_tables() + "\n"

    md += "## Compiler stages with different benchmarks\n"
    for test_case_dir in sorted(os.scandir(STAGES_DIR), key=lambda entry: entry.name):
        if test_case_dir.name in SKIPPED_TESTS[None]:
            continue

        md += f"### `{test_case_dir.name}`\n"
        input_path = os.path.join(test_case_dir, "input.py")
        with open(input_path, "r") as f:
            input_text = f.read()

        md += "#### Input\n"
        md += f"```python\n{input_text}\n```\n"

        ast = python_ast.parse(input_text, filename=input_path)
        restricted_ast = compiler.ast_to_restricted_ast(
            node=ast, filename=input_path, text=input_text
        )
        md += "#### Restricted AST\n"
        md += f"```python\n{restricted_ast}\n```\n"

        tac_cfg = compiler.restricted_ast_to_tac_cfg(restricted_ast)
        filename = f"images/{test_case_dir.name}_tac_cfg.png"
        path = os.path.join(args.path, filename)
        cfg_to_image(tac_cfg.body, path)
        md += "#### Three-address code CFG\n"
        md += f"![]({filename})\n"

        ssa = compiler.tac_cfg_to_ssa(tac_cfg)
        filename = f"images/{test_case_dir.name}_ssa.png"
        path = os.path.join(args.path, filename)
        cfg_to_image(ssa.body, path)
        md += "#### SSA\n"
        md += f"![]({filename})\n"

        compiler.replace_phi_with_mux(ssa)
        filename = f"images/{test_case_dir.name}_ssa_mux.png"
        path = os.path.join(args.path, filename)
        cfg_to_image(ssa.body, path)
        md += "#### SSA ϕ→MUX\n"
        md += f"![]({filename})\n"

        compiler.dead_code_elim(ssa)
        filename = f"images/{test_case_dir.name}_dead_code_elim.png"
        path = os.path.join(args.path, filename)
        cfg_to_image(ssa.body, path)
        md += "#### Dead code elimination\n"
        md += f"![]({filename})\n"

        loop_linear_code = compiler.ssa_to_loop_linear_code(ssa)
        md += "#### Linear code with loops\n"
        md += f"```python\n{loop_linear_code}\n```\n"

        dep_graph = compiler.DepGraph(loop_linear_code)
        filename = f"images/{test_case_dir.name}_dep_graph.png"
        path = os.path.join(args.path, filename)
        dep_graph_to_image(dep_graph, loop_linear_code, path)
        md += "#### Dependency graph\n"
        md += f"![]({filename})\n"

        compiler.vectorize.remove_infeasible_edges(loop_linear_code, dep_graph)
        filename = f"images/{test_case_dir.name}_remove_infeasible_edges.png"
        path = os.path.join(args.path, filename)
        dep_graph_to_image(dep_graph, loop_linear_code, path)
        md += "#### Removal of infeasible edges\n"
        md += f"![]({filename})\n"

        (loop_linear_code, type_env) = compiler.type_check(loop_linear_code, dep_graph)
        md += "#### Type Environment Before Vectorization\n"
        md += f"{type_env_to_table(type_env)}\n"

        (loop_linear_code, dep_graph) = compiler.vectorize.basic_vectorization_phase_1(
            loop_linear_code, type_env
        )
        md += "#### Basic Vectorization Phase 1\n"
        md += f"```python\n{loop_linear_code}\n```\n"
        filename = f"images/{test_case_dir.name}_bv_phase_1_dep_graph.png"
        path = os.path.join(args.path, filename)
        dep_graph_to_image(dep_graph, loop_linear_code, path)
        md += "#### Basic Vectorization Phase 1 (dependence graph)\n"
        md += f"![]({filename})\n"

        (
            loop_linear_code,
            dep_graph,
        ) = compiler.vectorize.basic_vectorization_phase_2(loop_linear_code)
        md += "#### Basic Vectorization Phase 2\n"
        md += f"```python\n{loop_linear_code}\n```\n"
        filename = f"images/{test_case_dir.name}_bv_phase_2_dep_graph.png"
        path = os.path.join(args.path, filename)
        dep_graph_to_image(dep_graph, loop_linear_code, path)
        md += "#### Basic Vectorization Phase 2 (dependence graph)\n"
        md += f"![]({filename})\n"

        (loop_linear_code, type_env) = compiler.type_check(loop_linear_code, dep_graph)
        md += "#### Type Environment After Vectorization\n"
        md += f"{type_env_to_table(type_env)}\n"

        for backend in Backend:
            if backend is Backend.MOTION:
                lang = "cpp"
            elif backend is Backend.MP_SPDZ:
                lang = "py"
            else:
                lang = ""
            backend_code = backend.render_function(loop_linear_code, type_env, True)
            md += f"#### {backend} code\n"
            md += f"```{lang}\n{backend_code}\n```\n"

    md_path = os.path.join(args.path, "README.md")
    with open(md_path, "w") as f:
        f.write(md)


if __name__ == "__main__":
    main()
