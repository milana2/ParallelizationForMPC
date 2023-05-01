import ast
import os
import sys
import subprocess
import unittest

import compiler
from compiler.backends import Backend

from . import context as test_context
from .backends import run_benchmark


class StagesTestCase(unittest.TestCase):
    maxDiff = None

    def test_stages(self):
        if test_context.BACKEND:
            self.skipTest("Only verifying output of example applications")

        for test_case_dir in os.scandir(test_context.STAGES_DIR):
            if test_case_dir.name in test_context.SKIPPED_TESTS[None]:
                continue

            print(f"Testing {test_case_dir.name}...")

            stages = dict()

            for stage_file in os.scandir(test_case_dir.path):
                if stage_file.is_file():
                    with open(stage_file.path, "r") as f:
                        stages[stage_file.name] = f.read().strip()

            node = ast.parse(stages["input.py"])

            node = compiler.ast_to_restricted_ast(node, "input.py", stages["input.py"])
            self.assertEqual(str(node), stages["restricted_ast.py"])

            cfg = compiler.restricted_ast_to_tac_cfg(node)
            self.assertEqual(str(cfg), stages["tac_cfg.txt"])

            ssa = compiler.tac_cfg_to_ssa(cfg)
            self.assertEqual(str(ssa), stages["ssa.txt"])

            compiler.replace_phi_with_mux(ssa)
            self.assertEqual(str(ssa), stages["ssa_mux.txt"])

            compiler.dead_code_elim(ssa)
            self.assertEqual(str(ssa), stages["dead_code_elim.txt"])

            loop_linear = compiler.ssa_to_loop_linear_code(ssa)
            self.assertEqual(str(loop_linear), stages["loop_linear.txt"])

            dep_graph = compiler.DepGraph(loop_linear)
            self.assertEqual(str(dep_graph), stages["dep_graph.txt"])

            compiler.vectorize.remove_infeasible_edges(loop_linear, dep_graph)
            self.assertEqual(
                str(dep_graph), stages["dep_graph_remove_infeasible_edges.txt"]
            )

            (loop_linear, type_env) = compiler.type_check(loop_linear, dep_graph)
            self.assertEqual(str(loop_linear), stages["unvectorized_linear.txt"])
            self.assertEqual(str(type_env), stages["unvectorized_type_env.txt"])

            (loop_linear, dep_graph) = compiler.vectorize.basic_vectorization_phase_1(
                loop_linear, type_env
            )
            self.assertEqual(str(loop_linear), stages["bv_phase_1.txt"])
            self.assertEqual(str(dep_graph), stages["bv_phase_1_dep_graph.txt"])

            (
                loop_linear,
                dep_graph,
            ) = compiler.vectorize.basic_vectorization_phase_2(loop_linear)
            self.assertEqual(str(loop_linear), stages["bv_phase_2.txt"])
            self.assertEqual(str(dep_graph), stages["bv_phase_2_dep_graph.txt"])

            (loop_linear, type_env) = compiler.type_check(loop_linear, dep_graph)
            self.assertEqual(str(loop_linear), stages["vectorized_linear.txt"])
            self.assertEqual(str(type_env), stages["vectorized_type_env.txt"])

            for backend in Backend:
                backend_code = backend.render_function(loop_linear, type_env, True)
                self.assertEqual(
                    str(backend_code), stages[f"{backend}_code.txt".lower()]
                )

    def test_example_apps(self):
        if test_context.BACKEND is None:
            self.skipTest("Skipping example application compilation")

        for test_case_dir in os.scandir(test_context.STAGES_DIR):
            name = test_case_dir.name
            if name in (
                test_context.SKIPPED_TESTS[None]
                + test_context.SKIPPED_TESTS[test_context.BACKEND]
            ):
                continue
            print(f"Testing {name}...")
            expected_output = get_test_case_expected_output(test_case_dir.path)
            for protocol in test_context.BACKEND.valid_protocols():
                print(f"    Protocol {protocol}...")
                for vectorized in (False, True):
                    output = run_benchmark(
                        test_context.BACKEND,
                        name,
                        test_case_dir.path,
                        protocol,
                        vectorized,
                    )
                    assert output
                    party0, party1 = output
                    self.assertEqual(party0.strip(), party1.strip())
                    self.assertEqual(party0.strip(), expected_output.strip())
                    self.assertEqual(party1.strip(), expected_output.strip())


def get_test_case_expected_output(test_case_dir: str) -> str:
    """
    Run the benchmark file in a Python interpreter to get the expected output
    for the test inputs.
    """

    input_fname = os.path.join(test_case_dir, "input.py")
    proc = subprocess.run(
        [sys.executable, input_fname],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return proc.stdout


def regenerate_stages():
    for test_case_dir in os.scandir(test_context.STAGES_DIR):
        if test_case_dir.name in test_context.SKIPPED_TESTS[None]:
            continue

        print(f"Regenerating {test_case_dir.name}...")
        with open(os.path.join(test_case_dir, "input.py"), "r") as f:
            input_text = f.read()

        node = ast.parse(input_text)

        node = compiler.ast_to_restricted_ast(node, "input.py", input_text)
        with open(os.path.join(test_case_dir, "restricted_ast.py"), "w") as f:
            f.write(f"{node}\n")

        cfg = compiler.restricted_ast_to_tac_cfg(node)
        with open(os.path.join(test_case_dir, "tac_cfg.txt"), "w") as f:
            f.write(f"{cfg}\n")

        ssa = compiler.tac_cfg_to_ssa(cfg)
        with open(os.path.join(test_case_dir, "ssa.txt"), "w") as f:
            f.write(f"{ssa}\n")

        compiler.replace_phi_with_mux(ssa)
        with open(os.path.join(test_case_dir, "ssa_mux.txt"), "w") as f:
            f.write(f"{ssa}\n")

        compiler.dead_code_elim(ssa)
        with open(os.path.join(test_case_dir, "dead_code_elim.txt"), "w") as f:
            f.write(f"{ssa}\n")

        loop_linear = compiler.ssa_to_loop_linear_code(ssa)
        with open(os.path.join(test_case_dir, "loop_linear.txt"), "w") as f:
            f.write(f"{loop_linear}\n")

        dep_graph = compiler.DepGraph(loop_linear)
        with open(os.path.join(test_case_dir, "dep_graph.txt"), "w") as f:
            f.write(f"{dep_graph}\n")

        compiler.vectorize.remove_infeasible_edges(loop_linear, dep_graph)
        with open(
            os.path.join(test_case_dir, "dep_graph_remove_infeasible_edges.txt"), "w"
        ) as f:
            f.write(f"{dep_graph}\n")

        (loop_linear, type_env) = compiler.type_check(loop_linear, dep_graph)
        with open(os.path.join(test_case_dir, "unvectorized_linear.txt"), "w") as f:
            f.write(f"{loop_linear}\n")
        with open(os.path.join(test_case_dir, "unvectorized_type_env.txt"), "w") as f:
            f.write(f"{type_env}\n")

        (loop_linear, dep_graph) = compiler.vectorize.basic_vectorization_phase_1(
            loop_linear, type_env
        )
        with open(os.path.join(test_case_dir, "bv_phase_1.txt"), "w") as f:
            f.write(f"{loop_linear}\n")
        with open(os.path.join(test_case_dir, "bv_phase_1_dep_graph.txt"), "w") as f:
            f.write(f"{dep_graph}\n")

        (
            loop_linear,
            dep_graph,
        ) = compiler.vectorize.basic_vectorization_phase_2(loop_linear)
        with open(os.path.join(test_case_dir, "bv_phase_2.txt"), "w") as f:
            f.write(f"{loop_linear}\n")
        with open(os.path.join(test_case_dir, "bv_phase_2_dep_graph.txt"), "w") as f:
            f.write(f"{dep_graph}\n")

        (loop_linear, type_env) = compiler.type_check(loop_linear, dep_graph)
        with open(os.path.join(test_case_dir, "vectorized_linear.txt"), "w") as f:
            f.write(f"{loop_linear}\n")
        with open(os.path.join(test_case_dir, "vectorized_type_env.txt"), "w") as f:
            f.write(f"{type_env}\n")

        for backend in Backend:
            backend_code = backend.render_function(loop_linear, type_env, True)
            with open(
                os.path.join(test_case_dir, f"{backend}_code.txt".lower()), "w"
            ) as f:
                f.write(f"{backend_code}\n")
