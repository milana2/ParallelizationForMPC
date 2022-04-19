from dataclasses import dataclass
import os
import shutil
import subprocess

import compiler
from . import statistics


@dataclass
class BenchmarkOutput:
    name: str
    output: str
    timing_stats: statistics.TimingStatistics
    circuit_stats: statistics.CircuitStatistics
    @classmethod
    def from_dictionary(cls, params):
        name = params['name']
        output = params['output']
        timing_stats = params['timing_stats']
        circuit_stats = params['circuit_stats']

        return cls(
            name=name,
            output=output,
            timing_stats=timing_stats,
            circuit_stats=circuit_stats
            )

    def to_dictionary(self):
        return {'name': self.name,
                'output': self.output,
                'timing_stats': self.timing_stats,
                'circuit_stats': self.circuit_stats,
                }


def run_benchmark(
    benchmark_name: str, benchmark_path: str, protocol: str, vectorized=True, timeout=600,
    cmd_args = [], compile=True, continue_on_error = False
) -> tuple[BenchmarkOutput, BenchmarkOutput]:
    input_fname = os.path.join(benchmark_path, "input.py")

    with open(input_fname, "r") as f:
        input_py = f.read().strip()

    app_path = os.path.join(
        benchmark_path, "motion_app" + "-" + protocol + ("-vectorized" if vectorized else "")
    )

    if compile:
        compiler.compile(
            f"{benchmark_name}.py", input_py, True, vectorized, app_path, True, protocol
        )

        subprocess.run(
            ["cmake", "-S", app_path, "-B", os.path.join(app_path, "build")],
            check=True,
        )

        subprocess.run(
            ["cmake", "--build", os.path.join(app_path, "build")],
            check=True,
        )

    # Create directories for output and MOTION logs
    party0_dir = os.path.join(app_path, "party0")
    if os.path.exists(party0_dir):
        shutil.rmtree(party0_dir)
    os.makedirs(party0_dir, exist_ok=True)

    party1_dir = os.path.join(app_path, "party1")
    if os.path.exists(party1_dir):
        shutil.rmtree(party1_dir)
    os.makedirs(party1_dir, exist_ok=True)

    # Run both parties
    exe_name = os.path.join(app_path, "build", benchmark_name)
    with subprocess.Popen(
        [
            exe_name,
            "--parties",
            "0,127.0.0.1,2300",
            "1,127.0.0.1,2301",
            "--my-id",
            "0",
        ] + cmd_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=party0_dir,
    ) as party0:
        with subprocess.Popen(
            [
                exe_name,
                "--parties",
                "0,127.0.0.1,2300",
                "1,127.0.0.1,2301",
                "--my-id",
                "1",
            ] + cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=party1_dir,
        ) as party1:
            # party0.wait(timeout)
            # party1.wait(timeout)
            # assert party0.stdout is not None
            # assert party0.stderr is not None
            # party0_stdout_raw = party0.stdout.read()
            # party0_stderr = party0.stderr.read()

            try:
                party0_stdout_raw, party0_stderr = party0.communicate(timeout)
                party1_stdout_raw, party1_stderr = party1.communicate(timeout)
            except subprocess.TimeoutExpired:
                party0.kill()
                party1.kill()
                party0_stdout_raw, party0_stderr = party0.communicate(timeout)
                party1_stdout_raw, party1_stderr = party1.communicate(timeout)

            with open(os.path.join(party0_dir, "stdout"), "w") as f:
                f.write(party0_stdout_raw)
            with open(os.path.join(party0_dir, "stderr"), "w") as f:
                f.write(party0_stderr)

            if(party0.returncode != 0 and party1.returncode != 0 and continue_on_error):
                return (
                    None, None
                )
            with open(os.path.join(party1_dir, "stdout"), "w") as f:
                f.write(party1_stdout_raw)
            with open(os.path.join(party1_dir, "stderr"), "w") as f:
                f.write(party1_stderr)

            party0_timing_stats = statistics.parse_timing_data(
                party0_stderr.split("\n")
            )
            party1_timing_stats = statistics.parse_timing_data(
                party1_stderr.split("\n")
            )

            party0_stdout_lines = party0_stdout_raw.split("\n")
            party0_output = party0_stdout_lines[0]
            party0_circuit_stats = statistics.parse_circuit_data(
                party0_stdout_lines[1:]
            )

            party1_stdout_lines = party1_stdout_raw.split("\n")
            party1_output = party1_stdout_lines[0]
            party1_circuit_stats = statistics.parse_circuit_data(
                party1_stdout_lines[1:]
            )

            return (
                BenchmarkOutput(
                    name=benchmark_name,
                    output=party0_output,
                    timing_stats=party0_timing_stats,
                    circuit_stats=party0_circuit_stats,
                ),
                BenchmarkOutput(
                    name=benchmark_name,
                    output=party1_output,
                    timing_stats=party1_timing_stats,
                    circuit_stats=party1_circuit_stats,
                ),
            )
