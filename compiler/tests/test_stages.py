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
