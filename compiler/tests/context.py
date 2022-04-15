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
    # The following tests cause issues since they don't loop from 0
    "longest_1s",
    "longest_even_0",
    # The following benchmarks are disabled because they take too long to run
    "kmeans_iteration",
]
