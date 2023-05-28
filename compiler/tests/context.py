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
        # AssertionError: '23926103924128485712268527085046455810' != '2'
        "db_variance",
        # AssertionError: assert all(array.vectorized_dims)
        "histogram",
        # TypeError: unsupported operand type(s) for &: 'sint' and 'sint'
        "longest_odd_10",
        # These benchmarks work now
        #"db_cross_join_trivial",
        #"mnist_relu", 
        #"cryptonets_max_pooling", 
        #"minimal_points", 
        #"psi", 
        #"convex_hull", 
        #"longest_102", 
        #"count_102",
        #"biometric_fast",
        #"max_dist_between_syms",
        #"count_123",
        #"max_sum_between_syms",
        #"inner_product", 
        #"biometric", 
        #"count_10s"
        #"chapterfour_figure_12",
    ],
}
