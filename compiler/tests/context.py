import os
from typing import Optional

from compiler.backends import Backend

TESTS_DIR = os.path.dirname(__file__)

STAGES_DIR = os.path.join(TESTS_DIR, "stages")

BACKEND: Optional[Backend] = None

SKIPPED_TESTS = {
    # Skipped in all backends
    None: [
        # These benchmarks will always be skipped (they're essentially pseudocode)
        "biometric_vectorized",
        # The following tests cause issues since they don't loop from 0
        "longest_1s",
        "longest_even_0",
        # The following benchmarks are disabled because they take too long to run
        "kmeans_iteration",
    ],
    # Skipped only in MOTION
    Backend.MOTION: [],
    # Skipped only in SPDZ
    Backend.MP_SPDZ: [
        # what():  SPDZ gfp memory overflow: 8872/8872
        "cryptonets_max_pooling",
        # Compiler.exceptions.CompilerError: Mismatch of instruction and register size: 75 != 375
        "db_cross_join_trivial",
        # AssertionError: '23926103924128485712268527085046455810' != '2'
        "db_variance",
        # AssertionError: assert all(array.vectorized_dims)
        "histogram",
        # TypeError: unsupported operand type(s) for &: 'sint' and 'sint'
        "longest_odd_10",
        # AssertionError: '([1, 2, 3], [4, 5, 6])' != '([1, 0, 0], [4, 0, 0])'
        "minimal_points",
        # what():  SPDZ gfp memory overflow: 10992/10992
        "mnist_relu",
        # AssertionError: '[0, 0, 0, 0, 0]' != '[4, 2, 3, 0, 10]'
        "psi",
        "chapterfour_figure_12",
        # Wrong result with semi-bin
        "convex_hull",
    ],
}
