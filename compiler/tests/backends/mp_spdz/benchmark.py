import os
import subprocess
from typing import Optional

import compiler
from compiler.backends import Backend


def run_benchmark(
    benchmark_name: str,
    benchmark_path: str,
    protocol: str,
    vectorized=True,
) -> Optional[tuple[str, str]]:
    input_fname = os.path.join(benchmark_path, "input.py")

    with open(input_fname, "r") as f:
        input_py = f.read().strip()

    submodule_path = Backend.MP_SPDZ.submodule_path()

    app_path = os.path.join(submodule_path, "Programs", "Source", "benchmark.mpc")

    compiler.compile(
        f"{benchmark_name}.py",
        input_py,
        Backend.MP_SPDZ,
        True,
        vectorized,
        app_path,
        True,
        protocol,
    )

    subprocess.run(["make", "setup"], cwd=submodule_path, check=True)

    player_data_dir = os.path.join(submodule_path, "Player-Data")
    os.mkdir(player_data_dir)
    with open(os.path.join(player_data_dir, "Input-P0-0"), "w") as f:
        f.write("1 2 3 4")
    with open(os.path.join(player_data_dir, "Input-P1-0"), "w") as f:
        f.write("1 2 3 4")

    subprocess.run(
        ["Scripts/compile-run.py", "-E", "mascot", "benchmark"],
        cwd=submodule_path,
        check=True,
    )
