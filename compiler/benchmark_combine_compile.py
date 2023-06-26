#!/usr/bin/env python3

import os
import timeit

import compiler
import compiler.backends
from tests.context import SKIPPED_TESTS


NUMBER = 100  # Number of iterations to average


def main():
    print(
        "Benchmark",
        "Backend",
        "Vec",
        "Time (ms)",
        sep="\t",
    )
    print("—" * 50)
    stages_dir = os.path.join("tests", "stages")
    for benchmark_name in os.listdir(stages_dir):
        benchmark_path = os.path.join(stages_dir, benchmark_name, "input.py")
        with open(benchmark_path, "r") as f:
            benchmark_code = f.read()
        for backend in compiler.backends.Backend:
            if benchmark_name in SKIPPED_TESTS[None] + SKIPPED_TESTS[backend]:
                continue
            for run_vectorization in (False, True):
                f = lambda: compiler.compile(
                    benchmark_name,
                    benchmark_code,
                    backend,
                    True,
                    run_vectorization,
                    None,
                    False,
                    "",
                )
                symbols = dict(globals())
                symbols.update(locals())
                print(
                    benchmark_name,
                    backend,
                    run_vectorization,
                    timeit.timeit("f()", globals=symbols, number=NUMBER)
                    / NUMBER
                    * 1000,
                    sep="\t",
                )


if __name__ == "__main__":
    main()
