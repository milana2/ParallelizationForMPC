
from argparse import ArgumentParser
from dataclasses import dataclass
import os
import sys
import subprocess

import logging
import logging.handlers
import random
import pickle

import compiler

from tests import context as test_context
from tests.benchmark import run_benchmark
from tests.benchmark import BenchmarkOutput

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
    handlers=[
        logging.handlers.RotatingFileHandler(
            "{0}.log".format(os.path.basename(__file__)),
             maxBytes=(1048576*5), backupCount=10
        )
    ])

fmt_str = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
formatter = logging.Formatter(fmt_str)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(formatter)

log = logging.getLogger(__name__)
log.addHandler(console);



@dataclass
class StatsForInputConfig:
    label: str
    p0: BenchmarkOutput
    p1: BenchmarkOutput
    p0_vectorized: BenchmarkOutput
    p1_vectorized: BenchmarkOutput


@dataclass
class StatsForBenchmark:
    label: str
    variations: list[StatsForInputConfig]

@dataclass
class InputArgs:
    label: str
    args: list[str]


random.seed(0) # Intentionally seeding with a known value, for reproducibility
def get_rand_ints(n):
    return [random.randint(1, 100) for i in range(n)]

def get_biometric_inputs()-> list[InputArgs]:
    all_args = []
    for config in [[4, 4], [4, 8], [4, 16], [4, 32], [4, 64], [4, 128]]:# [8, 64], [4, 256]]:
        D = config[0]
        N = config[1]
        args = [
        "--D", "{}".format(D),
        "--N", "{}".format(N),
        ]
        C = get_rand_ints(D)
        S = get_rand_ints(D * N)
        args.append("--C")
        args.extend(list(map(str, C)))
        args.append("--S")
        args.extend(list(map(str, S)))
        label = "D: {}, N: {}".format(D, N)
        all_args.append(InputArgs(label, args))
    return all_args

def get_psi_inputs()-> list[InputArgs]:
    all_args = []
    for config in [[4, 16], [16, 32]]:#, [16, 64], [16, 128], [16, 256], [16, 512]]:# [8, 64], [4, 256]]:
        SA = config[0]
        SB = config[1]
        args = [
        "--SA", "{}".format(SA),
        "--SB", "{}".format(SB),
        ]
        A = get_rand_ints(SA)
        B = get_rand_ints(SB)
        args.append("--A")
        args.extend(list(map(str, A)))
        args.append("--B")
        args.extend(list(map(str, B)))
        label = "SA: {}, SB: {}".format(SA, SB)
        all_args.append(InputArgs(label, args))
    return all_args

def get_inputs(name: str) -> list[InputArgs]:
    if name == "biometric":
         return get_biometric_inputs()
    # if name == "psi":
    #     return get_psi_inputs()
    return []

def print_benchmark_data(filename):
    with open(filename, "rb") as f:
        all_stats = pickle.load(f)

    log.info("Listing All Benchmark Stats")
    for bench_stat in all_stats:
        log.info("="*80)
        log.info(bench_stat.label)
        log.info("="*80);
        for v in bench_stat.variations:
            log.info("-"*80)
            log.info("{}".format(v.label))
            log.info("-"*80)
            ts0  = v.p0.timing_stats
            ts0v = v.p0_vectorized.timing_stats
            cs0  = v.p0.circuit_stats
            cs0v = v.p0_vectorized.circuit_stats
            ts1  = v.p1.timing_stats
            ts1v = v.p1_vectorized.timing_stats
            cs1  = v.p1.circuit_stats
            cs1v = v.p1_vectorized.circuit_stats

            log.info("Timing/Communication")
            for i in [ts0, ts0v, ts1, ts1v]:
                log.info("{} {} ms, {} {} ms, {} {} ms".format(i.preprocess_total.datapoint_name, i.preprocess_total.mean,
                    i.gates_setup.datapoint_name, i.gates_setup.mean,
                    i.gates_online.datapoint_name, i.gates_online.mean))
                comm = i.communication
                log.info("Send: {} MiB ({} Msgs) - Recv: {} MiB ({} Msgs)".format(
                    comm.send_size, comm.send_num_msgs, comm.recv_size, comm.recv_num_msgs))


            log.info("Circuit (Non-Vectorized vs Vectorized)")
            for i in [cs0, cs0v]:#, cs1, cs1v]: # circuit information should be identical for all parties
                log.info("Num Gates: {} In: {}, Out: {}, SIMD: {}, Non-SIMD: {}, Circ-Gen-Time: {} ms".format(
                    i.num_gates, i.num_inputs, i.num_outputs, i.num_simd_gates, i.num_nonsimd_gates, i.circuit_gen_time))


def run_paper_benchmarks(filename):
    all_stats = []
    for protocol in compiler.motion_backend.VALID_PROTOCOLS:
            for test_case_dir in os.scandir(test_context.STAGES_DIR):
                all_args = get_inputs(test_case_dir.name)
                if len(all_args) == 0:
                    continue;

                bench_stats = StatsForBenchmark("{} {}".format(protocol, test_case_dir.name), [])
                input_fname = os.path.join(test_case_dir.path, "input.py")
                
                compile = True
                for args in all_args:
                    #log.debug("args: {}".format(args.args))
                    log.info("Running {}-{} with label {}. (Non-Vectorized first, Vectorized second)".format(test_case_dir.name, 
                        protocol, args.label));
                    log.info("Arguments are: {}".format(args.args));
                
                    party0, party1 = run_benchmark(
                        test_case_dir.name, test_case_dir.path, protocol, False, None, args.args, compile
                    )

                    log.info("Non Vectorized output is {}".format(party0.output.strip()))
                    assert party0.output.strip() == party1.output.strip(), (party0.output.strip(), party1.output.strip())
                    party0_vectorized, party1_vectorized = run_benchmark(
                        test_case_dir.name, test_case_dir.path, protocol, True, None, args.args, compile
                    )
                    
                    compile = False

                    log.info("Vectorized output is {}".format(party0_vectorized.output.strip()))
                    assert party0_vectorized.output.strip() == party1_vectorized.output.strip(), \
                        (party0_vectorized.output.strip(), party1_vectorized.output.strip())
                    input_stats = StatsForInputConfig(args.label, party0, party1, party0_vectorized, party1_vectorized)

                    bench_stats.variations.append(input_stats)

                all_stats.append(bench_stats)
    with open(filename, "wb") as f:
        pickle.dump(all_stats, f)

    print_benchmark_data(filename)

def generate_graphs(source_data_file):
    with open(source_data_file, "rb") as f:
        all_stats = pickle.load(f)

    FILE_DIR = os.path.dirname(__file__)
    GRAPHS_DIR = os.path.join(FILE_DIR, "graphs")
    os.makedirs(GRAPHS_DIR, exist_ok=True)
    fname = 'g1.txt'
    file_path = os.path.join(GRAPHS_DIR, fname)
    with open(file_path, mode='w', encoding='utf-8') as f:
        log.info("Listing All Benchmark Stats")
        x = 1
        for bench_stat in all_stats:
            log.info("="*80)
            log.info(bench_stat.label)
            log.info("="*80);
            for v in bench_stat.variations:
                log.info("-"*80)
                log.info("{}".format(v.label))
                log.info("-"*80)
                ts0  = v.p0.timing_stats
                ts0v = v.p0_vectorized.timing_stats
                cs0  = v.p0.circuit_stats
                cs0v = v.p0_vectorized.circuit_stats
                ts1  = v.p1.timing_stats
                ts1v = v.p1_vectorized.timing_stats
                cs1  = v.p1.circuit_stats
                cs1v = v.p1_vectorized.circuit_stats

                log.info("Timing/Communication")
                for i in [ts0, ts0v, ts1, ts1v]:
                    log.info("{} {} ms, {} {} ms, {} {} ms".format(i.preprocess_total.datapoint_name, i.preprocess_total.mean,
                        i.gates_setup.datapoint_name, i.gates_setup.mean,
                        i.gates_online.datapoint_name, i.gates_online.mean))
                    comm = i.communication
                    log.info("Send: {} MiB ({} Msgs) - Recv: {} MiB ({} Msgs)".format(
                        comm.send_size, comm.send_num_msgs, comm.recv_size, comm.recv_num_msgs))


                log.info("Circuit (Non-Vectorized vs Vectorized)")
                for i in [cs0, cs0v]:#, cs1, cs1v]: # circuit information should be identical for all parties
                    log.info("Num Gates: {} In: {}, Out: {}, SIMD: {}, Non-SIMD: {}, Circ-Gen-Time: {} ms".format(
                        i.num_gates, i.num_inputs, i.num_outputs, i.num_simd_gates, i.num_nonsimd_gates, i.circuit_gen_time))
                x += 1

    
    
    # with subprocess.Popen(
    #     [
    #         "gnuplot",
    #         "g1.gnu",
    #     ],
    #     stdout=subprocess.PIPE,
    #     stderr=subprocess.PIPE,
    #     text=True,
    #     cwd=GRAPHS_DIR
    # ) as gnuplot:
    #     gnuplot.wait()

if __name__ == "__main__":
    parser = ArgumentParser(
        description="runs and collects benchmarks statistics for the paper. (assumes correct network config)")
    parser.add_argument('-g', "--graphs",
        action="store_true",
        help="generates graphs from benchmarks",
    )
    parser.add_argument('-f', '--file', nargs='?', 
    help="file containing benchmark data", 
    default="benchmarks.pickle",
    )
    args = parser.parse_args()

    if args.graphs:
        generate_graphs(args.file)
    else:
        run_paper_benchmarks(args.file)

