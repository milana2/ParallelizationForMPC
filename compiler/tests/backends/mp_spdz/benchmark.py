import shutil
import os
import subprocess
import re

import compiler
from compiler.backends import Backend


class BenchmarkOutput:
    result: str
    time_seconds: float
    data_sent_mb: float
    rounds: int
    global_data_sent_mb: float

    def __init__(self, stdout: str) -> None:
        def parse(pattern: str) -> tuple[str, ...]:
            m = re.search(rf"^\s*{pattern}\s*$", stdout, re.MULTILINE)
            assert m is not None, repr(stdout)
            return m.groups()

        self.result = parse(r"MPC BENCHMARK OUTPUT (.+)")[0]
        self.time_seconds = float(parse(r"Time = (.+) seconds")[0])
        data_sent_mb, rounds = parse(
            r"Data sent = (.+) MB in ~(.+) rounds \(party 0; use '-v' for more details\)",
        )
        self.data_sent_mb = float(data_sent_mb)
        self.rounds = int(rounds)
        self.global_data_sent_mb = float(
            parse(r"Global data sent = (.+) MB \(all parties\)")[0]
        )


def run_benchmark(
    benchmark_name: str,
    benchmark_path: str,
    protocol: str,
    vectorized=True,
    timeout=600,
) -> BenchmarkOutput:
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

    # Copy vectorization library so compiled programs can use it
    shutil.copyfile(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "compiler",
            "backends",
            "mp_spdz",
            "library.py",
        ),
        os.path.join(submodule_path, "vectorization_library.py"),
    )

    # Write an indicator file when running `make setup` so it only needs to run once
    setup_indicator_path = os.path.join(submodule_path, ".ran-make-setup")
    if not os.path.exists(setup_indicator_path):
        subprocess.run(["make", "setup"], cwd=submodule_path, check=True)
        with open(setup_indicator_path, "w") as _:
            pass

    p = subprocess.Popen(
        ["Scripts/compile-run.py", "-E", protocol, "benchmark"],
        cwd=submodule_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = p.communicate(timeout=timeout)
    assert p.returncode == 0, stderr
    return BenchmarkOutput(stdout)
