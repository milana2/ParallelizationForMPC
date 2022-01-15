import os
import unittest
import ast

import compiler

from .context import STAGES_DIR


class StagesTestCase(unittest.TestCase):
    maxDiff = None

    def test_stages(self):
        for test_case_dir in os.scandir(STAGES_DIR):
            print(f"Testing {test_case_dir.name}...")

            stages = dict()

            for stage_file in os.scandir(test_case_dir.path):
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

            (loop_linear, dep_graph) = compiler.vectorize.refine_array_mux(
                loop_linear, dep_graph
            )
            self.assertEqual(str(loop_linear), stages["refine_array_mux.txt"])
            self.assertEqual(str(dep_graph), stages["refine_array_mux_dep_graph.txt"])

            type_env = compiler.type_check(loop_linear, dep_graph)
            self.assertEqual(str(type_env), stages["type_env.txt"])


def regenerate_stages():
    for test_case_dir in os.scandir(STAGES_DIR):
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

        (loop_linear, dep_graph) = compiler.vectorize.refine_array_mux(
            loop_linear, dep_graph
        )
        with open(os.path.join(test_case_dir, "refine_array_mux.txt"), "w") as f:
            f.write(f"{loop_linear}\n")
        with open(
            os.path.join(test_case_dir, "refine_array_mux_dep_graph.txt"), "w"
        ) as f:
            f.write(f"{dep_graph}\n")

        type_env = compiler.type_check(loop_linear, dep_graph)
        with open(os.path.join(test_case_dir, "type_env.txt"), "w") as f:
            f.write(f"{type_env}\n")
