import os

TESTS_DIR = os.path.dirname(__file__)

STAGES_DIR = os.path.join(TESTS_DIR, "stages")

RUN_EXAMPLE_APPS = False

SKIPPED_TESTS = [
    # These benchmarks will always be skipped (they're essentially pseudocode)
    "biometric_fast",
    "biometric_vectorized",
    # These benchmarks fail because they involve appending to arrays
    "convex_hull",
    # TODO: figure out why these tests are failing:
    "chapterfour_figure_12",
    "longest_odd_10",
    # The following tests cause issues since they don't loop from 0
    "longest_1s",
    "longest_even_0",
    # The tests beyond this point fail to compile since they return a vector
    # Once our test harness can handle this, they can be re-enabled
    "cross_join",
    "cross_join_trivial",
    "gauss_decomp",
    "infeasible_edges_example",
    # The following benchmarks are disabled because they take too long to run
    "kmeans_iteration",
]
