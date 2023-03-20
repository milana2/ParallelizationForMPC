from typing import Optional

from compiler.backends import Backend
from compiler.util import assert_never
from .motion.benchmark import run_benchmark as motion_run_benchmark
from .mp_spdz.benchmark import run_benchmark as mp_spdz_run_benchmark


def run_benchmark(
    backend: Backend,
    benchmark_name: str,
    benchmark_path: str,
    protocol: str,
    vectorized=True,
) -> Optional[tuple[str, str]]:
    if backend is Backend.MOTION:
        result = motion_run_benchmark(
            benchmark_name, benchmark_path, protocol, vectorized
        )
        if result is None:
            return None
        else:
            party0, party1 = result
            return (party0.output, party1.output)
    elif backend is Backend.MP_SPDZ:
        output = mp_spdz_run_benchmark(
            benchmark_name, benchmark_path, protocol, vectorized
        )
        return (output, output)
    else:
        assert_never(backend)
