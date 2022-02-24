import os

TESTS_DIR = os.path.dirname(__file__)

STAGES_DIR = os.path.join(TESTS_DIR, "stages")

RUN_EXAMPLE_APPS = False

SKIPPED_TESTS = [
    "biometric_fast",
    "convex_hull",
    "histogram",
    "minimal_points",
    "psi",
    # The tests beyond this point fail to compile since they return a vector
    # Once our test harness can handle this, they can be re-enabled
    "cross_join",
    "cross_join_trivial",
    "gauss_decomp",
    "infeasible_edges_example",
]
