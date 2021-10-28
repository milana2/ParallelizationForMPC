import sys
import os

TESTS_DIR = os.path.dirname(__file__)

STAGES_DIR = os.path.join(TESTS_DIR, "stages")

COMPILER_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))

sys.path.insert(0, COMPILER_DIR)

import compiler
