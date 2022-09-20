import logging.handlers
import os
import random
import socket
import subprocess
from argparse import ArgumentParser
from dataclasses import dataclass

from tests import context as test_context
from tests.benchmark import run_benchmark, compile_benchmark, run_benchmark_for_party, BenchmarkOutput
from utils import PartyReadyReq
from utils import json_serialize, json_deserialize, StatsForInputConfig, StatsForTask, RunBenchmarkReq
from utils import read_message, write_message

SERVER_PORT = 42142
CONNECTION_TIMEOUT = 3000
MPC_PARTY_SERVER_ID = "0"
MPC_PARTY_CLIENT_ID = "1"
NUM_ITERS = 5

GMW_PROTOCOL = "BooleanGmw"
BMR_PROTOCOL = "Bmr"

FILE_DIR = os.path.dirname(__file__)
BENCHDATA_DIR = os.path.join(FILE_DIR, "benchdata")
LAN_DIR = os.path.join(BENCHDATA_DIR, "lan")
LAN_GRAPHS_DIR = os.path.join(LAN_DIR, "graphs")
WAN_DIR = os.path.join(BENCHDATA_DIR, "wan")
WAN_GRAPHS_DIR = os.path.join(WAN_DIR, "graphs")
COMPARISON_GRAPHS_DIR = os.path.join(BENCHDATA_DIR, "comparison-graphs")
GRAPH_EXT = ".tex"

os.makedirs(BENCHDATA_DIR, exist_ok=True)
os.makedirs(LAN_DIR, exist_ok=True)
os.makedirs(LAN_GRAPHS_DIR, exist_ok=True)
os.makedirs(WAN_DIR, exist_ok=True)
os.makedirs(WAN_GRAPHS_DIR, exist_ok=True)
os.makedirs(COMPARISON_GRAPHS_DIR, exist_ok=True)

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
log.addHandler(console)


@dataclass
class InputArgs:
    label: str
    args: list[str]


random.seed(0) # Intentionally seeding with a known value, for reproducibility


def get_rand_ints(n, min=1, max=100):
    return [random.randint(min, max) for i in range(n)]


def get_biometric_inputs() -> tuple[list[InputArgs], int]:
    all_args = []
    non_vec_up_to = 0 #6# Only run non-vectorized benchmark upto this index
    # for config in [[4, 4], [4, 8], [4, 16], [4, 32], [4, 64], [4, 128], [4, 256], [4, 512], [4, 1024], [4, 2048], [4, 4096]]:
    for config in [[4, 128], [4, 4096]]:
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
    return (all_args, non_vec_up_to)

def get_biometric_fast_inputs() -> tuple[list[InputArgs], int]:
    all_args = []
    non_vec_up_to = 0 #6 # Only run non-vectorized benchmark upto this index
    # for config in [[4, 4], [4, 8], [4, 16], [4, 32], [4, 64], [4, 128], [4, 256], [4, 512], [4, 1024], [4, 2048], [4, 4096]]:
    for config in [[4, 128], [4, 4096]]:
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

        two_C = [2 * C[i] for i in range(D)]
        args.append("--two_C")
        args.extend(list(map(str, two_C)))
        C_sqr_sum = sum(val * val for val in C)
        args.append("--C_sqr_sum")
        args.append(str(C_sqr_sum))
        S_sqr_sum = [sum(S[i * D + j] * S[i * D + j] for j in range(D)) for i in range(N)]
        args.append("--S_sqr_sum")
        args.extend(list(map(str, S_sqr_sum)))
        differences = [0] * D
        args.append("--differences")
        args.extend(list(map(str, differences)))

        label = "D: {}, N: {}".format(D, N)
        all_args.append(InputArgs(label, args))
    return (all_args, non_vec_up_to)

def get_chapterfour_figure_12_inputs() -> tuple[list[InputArgs], int]:
    all_args = []
    non_vec_up_to = 6
    x = random.randint(1, 100)
    y = random.randint(1, 100)
    args = [
    "--x", str(x),
    "--y", str(y)
    ]
    label = "x={}, y={}".format(x, y)
    all_args.append(InputArgs(label, args))
    return (all_args, non_vec_up_to)

def get_convex_hull_inputs():
    all_args = []
    non_vec_up_to = 0
    #for N in [4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]:
    for N in [32, 256]:
        args = [
        "--N", "{}".format(N),
        ]
        X_coords = get_rand_ints(N)
        Y_coords = get_rand_ints(N)
        result_X = get_rand_ints(N)
        result_Y = get_rand_ints(N)
        args.append("--X_coords")
        args.extend(list(map(str, X_coords)))
        args.append("--Y_coords")
        args.extend(list(map(str, Y_coords)))
        args.append("--result_X")
        args.extend(list(map(str, result_X)))
        args.append("--result_Y")
        args.extend(list(map(str, result_Y)))
        label = "N: {}".format(N)
        all_args.append(InputArgs(label, args))
    return (all_args, non_vec_up_to)

def get_count_102_inputs():
    all_args = []
    non_vec_up_to = 0
    #for N in [8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]:
    for N in [1024, 4096]:
        args = [
        "--N", "{}".format(N),
        ]
        Seq = get_rand_ints(N, min=0, max=2)
        Syms = [1, 0, 2]
        args.append("--Seq")
        args.extend(list(map(str, Seq)))
        args.append("--Syms")
        args.extend(list(map(str, Syms)))
        label = "N: {}".format(N)
        all_args.append(InputArgs(label, args))
    return (all_args, non_vec_up_to)

def get_count_10s_inputs():
    all_args = []
    non_vec_up_to = 0
    #for N in [8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]:
    for N in [1024, 4096]:
        args = [
        "--N", "{}".format(N),
        ]
        Seq = get_rand_ints(N, min=0, max=2)
        Syms = [0, 1]
        args.append("--Seq")
        args.extend(list(map(str, Seq)))
        args.append("--Syms")
        args.extend(list(map(str, Syms)))
        label = "N: {}".format(N)
        all_args.append(InputArgs(label, args))
    return (all_args, non_vec_up_to)

def get_count_123_inputs():
    all_args = []
    non_vec_up_to = 0
    #for N in [8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]:
    for N in [1024, 4096]:
        args = [
        "--N", "{}".format(N),
        ]
        Seq = get_rand_ints(N, min=1, max=4)
        Syms = [1, 2, 3]
        args.append("--Seq")
        args.extend(list(map(str, Seq)))
        args.append("--Syms")
        args.extend(list(map(str, Syms)))
        label = "N: {}".format(N)
        all_args.append(InputArgs(label, args))
    return (all_args, non_vec_up_to)

def get_cryptonets_max_pooling_inputs():
    all_args = []
    non_vec_up_to = 0
    #for config in [[4, 4], [8, 8], [16, 16], [32, 32], [64, 64]]:
    for config in [[64, 64]]:
        rows = config[0]
        cols = config[1]
        rows_res = rows // 2
        cols_res = cols // 2

        args = [
        "--cols", str(cols),
        "--rows", str(rows),
        "--cols_res", str(cols_res),
        "--rows_res", str(rows_res)
        ]
        vals = [i + 2 for i in range(rows * cols)]
        output_size = int(cols * rows / 4)
        OUTPUT_res = [0] * output_size
        args.append("--vals")
        args.extend(list(map(str, vals)))
        args.append("--OUTPUT_res")
        args.extend(list(map(str, OUTPUT_res)))
        label = "rows: {}, cols: {}".format(rows, cols)
        all_args.append(InputArgs(label, args))
    return (all_args, non_vec_up_to)

def get_db_cross_join_trivial_inputs():
    all_args = []
    non_vec_up_to = 0
    #for N in [4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048]:
    for N in [32, 64]:
        Len_A = N
        Len_B = N
        args = [
        "--Len_A", str(Len_A),
        "--Len_B", str(Len_B)
        ]
        A = get_rand_ints(Len_A * 2)
        B = get_rand_ints(Len_B * 2)
        res = [0 for i in range(Len_A * Len_B * 3)]
        args.append("--A")
        args.extend(list(map(str, A)))
        args.append("--B")
        args.extend(list(map(str, B)))
        args.append("--res")
        args.extend(list(map(str, res)))
        label = "{}, {}".format(Len_A, Len_B)
        all_args.append(InputArgs(label, args))
    return (all_args, non_vec_up_to)

def get_db_variance_inputs():
    all_args = []
    non_vec_up_to = 0
    #for N in [8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]:
    for N in [512, 4096]:
        args = [
        "--len", "{}".format(N),
        ]
        A = get_rand_ints(N)
        V = [0 for i in range(N)]
        args.append("--A")
        args.extend(list(map(str, A)))
        args.append("--V")
        args.extend(list(map(str, V)))
        label = "len: {}".format(N)
        all_args.append(InputArgs(label, args))
    return (all_args, non_vec_up_to)

def get_histogram_inputs():
    all_args = []
    num_bins = 5
    non_vec_up_to = 0
    #for N in [8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]:
    for N in [512, 4096]:
        args = [
        "--num_bins", "{}".format(num_bins),
        "--N", "{}".format(N),
        ]
        A = get_rand_ints(N, min=0, max=num_bins-1)
        B = get_rand_ints(N)
        R = [0 for i in range(N)]
        args.append("--A")
        args.extend(list(map(str, A)))
        args.append("--B")
        args.extend(list(map(str, B)))
        args.append("--result")
        args.extend(list(map(str, R)))
        label = "N: {}".format(N)
        all_args.append(InputArgs(label, args))
    return (all_args, non_vec_up_to)

def get_inner_product_inputs()-> tuple[list[InputArgs], int]:
    all_args = []
    non_vec_up_to = 0#8
    #for N in [4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]:
    for N in [512, 4096]:
        args = [
        "--N", "{}".format(N),
        ]
        A = get_rand_ints(N)
        B = get_rand_ints(N)
        args.append("--A")
        args.extend(list(map(str, A)))
        args.append("--B")
        args.extend(list(map(str, B)))
        label = "N: {}".format(N)
        all_args.append(InputArgs(label, args))
    return (all_args, non_vec_up_to)

def get_kmeans_iteration_inputs():
    all_args = []
    num_bins = 5
    non_vec_up_to = 0
    #for config in [[32, 5], [32, 8], [64, 8], [128, 8], [200, 5], [256, 8]]:
    for config in [[32, 5], [256, 8]]:
        len = config[0]
        num_cluster = config[1]
        data_x = [i for i in range(len)]
        data_y = [len - i for i in range(len)]
        cluster_x = [i for i in range(num_cluster)]
        cluster_y = [i + 1 for i in range(num_cluster)]
        OUTPUT_cluster_x = [0 for i in range(num_cluster)]
        OUTPUT_cluster_y = [0 for i in range(num_cluster)]
        bestMap = [0 for i in range(len)]

        args = [
        "--len", str(len),
        "--num_cluster", str(num_cluster),
        ]
        args.append("--data_x")
        args.extend(list(map(str, data_x)))
        args.append("--data_y")
        args.extend(list(map(str, data_y)))
        args.append("--cluster_x")
        args.extend(list(map(str, cluster_x)))
        args.append("--cluster_y")
        args.extend(list(map(str, cluster_y)))
        args.append("--OUTPUT_cluster_x")
        args.extend(list(map(str, OUTPUT_cluster_x)))
        args.append("--OUTPUT_cluster_y")
        args.extend(list(map(str, OUTPUT_cluster_y)))
        args.append("--bestMap")
        args.extend(list(map(str, bestMap)))

        label = "len1: {}, len2: {}".format(len, num_cluster)
        all_args.append(InputArgs(label, args))
    return (all_args, non_vec_up_to)

def get_longest_odd_10_inputs():
    all_args = []
    non_vec_up_to = 0
    #for N in [8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]:
    for N in [2048]:
        args = [
        "--N", str(N),
        ]
        Seq = get_rand_ints(N, min=0, max=1)
        Syms = [0, 1]
        args.append("--Seq")
        args.extend(list(map(str, Seq)))
        args.append("--Syms")
        args.extend(list(map(str, Syms)))
        label = "N: {}".format(N)
        all_args.append(InputArgs(label, args))
    return (all_args, non_vec_up_to)

def get_max_dist_between_syms_inputs():
    all_args = []
    non_vec_up_to = 0
    # for N in [8, 16, 32, 64, 128, 256, 512, 1024, 4096]:
    for N in [1024, 2048]:
        args = [
        "--N", "{}".format(N),
        ]
        Seq = get_rand_ints(N)
        some_i = random.randint(0, len(Seq)-1)
        Sym = Seq[some_i]
        args.append("--Seq")
        args.extend(list(map(str, Seq)))
        args.append("--Sym")
        args.append(str(Sym))
        label = "N: {}".format(N)
        all_args.append(InputArgs(label, args))
    return (all_args, non_vec_up_to)

def get_mnist_relu_inputs()-> tuple[list[InputArgs], int]:
    all_args = []
    non_vec_up_to = 0
    #for config in [[16, 16], [16, 32], [16, 64], [16, 128], [16, 256], [16, 512], [16, 1024]]:
    for config in [[16, 512], [16, 2048]]:
        len_inner = config[0]
        len_outer = config[1]
        args = [
        "--len_inner", "{}".format(len_inner),
        "--len_outer", "{}".format(len_outer),
        ]
        input = [(i % 2) for i in range(len_inner * len_outer)]
        OUTPUT_res = [0 for i in range(len_inner * len_outer)]
        args.append("--input")
        args.extend(list(map(str, input)))
        args.append("--OUTPUT_res")
        args.extend(list(map(str, OUTPUT_res)))
        label = "{}, {}".format(len_inner, len_outer)
        all_args.append(InputArgs(label, args))
    return (all_args, non_vec_up_to)

def get_psi_inputs()-> tuple[list[InputArgs], int]:
    all_args = []
    non_vec_up_to = 0
    #for config in [[16, 16], [32, 32], [64, 64], [128, 128], [256, 256], [512, 512], [1024, 1024]]:#[2048, 2084], [4096, 4096]]:
    for config in [[128, 128], [1024, 1024]]:
        SA = config[0]
        SB = config[1]
        args = [
        "--SA", "{}".format(SA),
        "--SB", "{}".format(SB),
        ]
        A = get_rand_ints(SA)
        B = get_rand_ints(SB)
        result = [0 for i in range(SA)]
        args.append("--A")
        args.extend(list(map(str, A)))
        args.append("--B")
        args.extend(list(map(str, B)))
        args.append("--result")
        args.extend(list(map(str, result)))
        label = "SA: {}, SB: {}".format(SA, SB)
        all_args.append(InputArgs(label, args))
    return all_args, non_vec_up_to


def get_inputs(name: str) -> tuple[list[InputArgs], int]:
    if name == "biometric":
        return get_biometric_inputs()
    # if name == "biometric_fast":
    #     return get_biometric_fast_inputs()
    # # if name == "chapterfour_figure_12": # millionaire's problem, not interesting
    # #     return get_chapterfour_figure_12_inputs()
    # if name == "convex_hull" or name == "minimal_points":
    #     return get_convex_hull_inputs()
    # if name ==  name == "count_102" or "longest_102":
    #     return get_count_102_inputs()
    # if name == "count_10s":
    #     return get_count_10s_inputs()
    # # if name == "count_123":
    # #     return get_count_123_inputs()
    # if name == "cryptonets_max_pooling":
    #     return get_cryptonets_max_pooling_inputs()
    # if name == "db_cross_join_trivial": # could only do up to 64
    #     return get_db_cross_join_trivial_inputs()
    # if name == "db_variance":
    #     return get_db_variance_inputs()
    # if name == "histogram":
    #     return get_histogram_inputs()
    # if name == "inner_product":
    #     return get_inner_product_inputs()
    # if name == "kmeans_iteration":
    #     return get_kmeans_iteration_inputs()
    # # if name == "longest_odd_10": # could not run for 4096
    # #     return get_longest_odd_10_inputs()
    # if name == "max_dist_between_syms": # or name == "max_sum_between_syms":
    #     return get_max_dist_between_syms_inputs()
    # if name == "mnist_relu":
    #     return get_mnist_relu_inputs()
    # if name == "psi": # could not run from 2048 and 4096
    #     return get_psi_inputs()
    return [[], 0]


def print_protocol_stats(non_vec, vec):
    log.info("Timing/Communication")
    for cs in range(len(vec)):
        if non_vec[cs] is not None:
            ts = non_vec[cs].timing_stats
            log.info("Party {} NonVec".format(cs))
            log.info("{} {} ms, {} {} ms, {} {} ms".format(ts.preprocess_total.datapoint_name,
                                                           ts.preprocess_total.mean, ts.gates_setup.datapoint_name,
                                                           ts.gates_setup.mean,
                                                           ts.gates_online.datapoint_name, ts.gates_online.mean))
            comm = ts.communication
            log.info("Send: {} MiB ({} Msgs) - Recv: {} MiB ({} Msgs)".format(
                comm.send_size, comm.send_num_msgs, comm.recv_size, comm.recv_num_msgs))

        ts = vec[cs].timing_stats
        log.info("Party {} Vectorized".format(cs))
        log.info("{} {} ms, {} {} ms, {} {} ms".format(ts.preprocess_total.datapoint_name,
                                                       ts.preprocess_total.mean, ts.gates_setup.datapoint_name,
                                                       ts.gates_setup.mean,
                                                       ts.gates_online.datapoint_name, ts.gates_online.mean))
        comm = ts.communication
        log.info("Send: {} MiB ({} Msgs) - Recv: {} MiB ({} Msgs)".format(
            comm.send_size, comm.send_num_msgs, comm.recv_size, comm.recv_num_msgs))

    log.info("Circuit (Non-Vectorized vs Vectorized)")
    for party_stat in [non_vec[0], vec[0]]:
        if party_stat is None:
            continue
        cs = party_stat.circuit_stats
        log.info("Num Gates: {} In: {}, Out: {}, SIMD: {}, Non-SIMD: {}, Circ-Gen-Time: {} ms".format(
            cs.num_gates, cs.num_inputs, cs.num_outputs, cs.num_simd_gates, cs.num_nonsimd_gates,
            cs.circuit_gen_time))


def print_benchmark_data(all_stats):
    log.info("Listing All Benchmark Stats")
    for task_stats in all_stats:
        log.info("="*80)
        log.info(task_stats.label)
        log.info("="*80);
        for v in task_stats.input_configs:
            log.info("-"*40)
            log.info("{} - GMW".format(v.label))
            log.info("-"*40)

            print_protocol_stats(v.gmw, v.gmw_vec)

            log.info("-"*40)
            log.info("{} - BMR".format(v.label))
            log.info("-"*40)
            print_protocol_stats(v.bmr, v.bmr_vec)


def update_benchmark_json(task_stats, input_stats):
    task_stats.input_configs.append(input_stats)
    log.info("task {} input config {} DONE".format(task_stats.label, input_stats.label))

    file_path = os.path.join(FILE_DIR, "{}.json".format(task_stats.label))
    with open(file_path, "w", encoding='utf-8') as f:
        json_str = json_serialize(task_stats)
        f.write(json_str)

def run_paper_benchmarks():
    all_stats = []
    for test_case_dir in os.scandir(test_context.STAGES_DIR):
        if test_case_dir.name in test_context.SKIPPED_TESTS:
                continue

        all_args, non_vec_up_to = get_inputs(test_case_dir.name)
        if len(all_args) == 0:
            continue;

        task_stats = StatsForTask(test_case_dir.name, [])
        compile = True
        i = 0
        non_vec_failed = False
        for args in all_args:
            log.info("\n{} - arguments: {}".format(test_case_dir.name, args.args));

            gmw_p0 = gmw_p1 = None
            if (i < non_vec_up_to) and not non_vec_failed:
                log.info("Running GMW Non Vectorized {} {}".format(test_case_dir.name, args.label));
                gmw_p0, gmw_p1 = run_benchmark(
                    test_case_dir.name, test_case_dir.path, GMW_PROTOCOL, False, None, args.args, compile,
                    continue_on_error=True
                )
                if gmw_p0 is not None and gmw_p1 is not None:
                    log.info("GMW Non Vectorized output is {}".format(gmw_p0.output.strip()))
                    assert gmw_p0.output.strip() == gmw_p1.output.strip(), \
                        (gmw_p0.output.strip(), gmw_p1.output.strip())
                else:
                    log.warning("GMW Non Vectorized FAILED! Will not run Non-Vectorized from now.")
                    non_vec_failed = True

            log.info("Running GMW Vectorized {} {}".format(test_case_dir.name, args.label));
            gmw_vec_p0, gmw_vec_p1 = run_benchmark(
                test_case_dir.name, test_case_dir.path, GMW_PROTOCOL, True, None, args.args, compile,
                continue_on_error=True
            )

            if(gmw_vec_p0 is not None and gmw_vec_p1 is not None):
                log.info("GMW Vectorized output is {}".format(gmw_vec_p0.output.strip()))
                assert gmw_vec_p0.output.strip() == gmw_vec_p1.output.strip(), \
                    (gmw_vec_p0.output.strip(), gmw_vec_p1.output.strip())
            else:
                log.warning("GMW Vectorized FAILED!")

            bmr_p0 = bmr_p1 = None
            if (i < non_vec_up_to) and not non_vec_failed:
                log.info("Running BMR Non Vectorized {} {}".format(test_case_dir.name, args.label));
                bmr_p0, bmr_p1 = run_benchmark(
                    test_case_dir.name, test_case_dir.path, BMR_PROTOCOL, False, None, args.args, compile,
                    continue_on_error=True
                )
                if bmr_p0 is not None and bmr_p1 is not None:
                    log.info("BMR Non Vectorized output is {}".format(bmr_p0.output.strip()))
                    assert bmr_p0.output.strip() == bmr_p1.output.strip(), \
                        (bmr_p0.output.strip(), bmr_p1.output.strip())
                else:
                    log.warning("BMR Non Vectorized FAILED! Will not run Non-Vectorized from now.")
                    non_vec_failed = True

            log.info("Running BMR Vectorized {} {}".format(test_case_dir.name, args.label));
            bmr_vec_p0, bmr_vec_p1 = run_benchmark(
                test_case_dir.name, test_case_dir.path, BMR_PROTOCOL, True, None, args.args, compile,
                continue_on_error=True
            )

            if bmr_vec_p0 is not None and bmr_vec_p1 is not None:
                log.info("BMR Vectorized output is {}".format(bmr_vec_p0.output.strip()))
                assert bmr_vec_p0.output.strip() == bmr_vec_p1.output.strip(), \
                    (bmr_vec_p0.output.strip(), bmr_vec_p1.output.strip())
            else:
                log.warning("BMR Vectorized FAILED!")

            compile = False

            if gmw_p0 is None and gmw_vec_p0 is None and bmr_p0 is None and bmr_vec_p0 is None:
                log.warning("{}, {} No version ran on this iteration.".format(test_case_dir.name,
                    args.label))
            else:
                input_stats = StatsForInputConfig(args.label, [gmw_p0, gmw_p1], [gmw_vec_p0, gmw_vec_p1],
                                                  [bmr_p0, bmr_p1], [bmr_vec_p0, bmr_vec_p1])
                update_benchmark_json(task_stats, input_stats)

            i += 1

        all_stats.append(task_stats)
        log.info("task {} DONE".format(task_stats.label))
    print_benchmark_data(all_stats)


def compile_all_benchmarks():
    for test_case_dir in os.scandir(test_context.STAGES_DIR):
        if test_case_dir.name in test_context.SKIPPED_TESTS:
                continue
        all_args, non_vec_up_to = get_inputs(test_case_dir.name)
        if len(all_args) == 0:
            continue
        log.info("Compiling {} ...".format(test_case_dir.name))
        compile_benchmark(test_case_dir.name, test_case_dir.path, GMW_PROTOCOL, False)
        compile_benchmark(test_case_dir.name, test_case_dir.path, GMW_PROTOCOL, True)
        compile_benchmark(test_case_dir.name, test_case_dir.path, BMR_PROTOCOL, False)
        compile_benchmark(test_case_dir.name, test_case_dir.path, BMR_PROTOCOL, True)
        if test_case_dir.name == "inner_product":
            compile_benchmark(test_case_dir.name, test_case_dir.path, "ArithmeticGmw", False)
            compile_benchmark(test_case_dir.name, test_case_dir.path, "ArithmeticGmw", True)


@dataclass
class Party:
    id: int
    address: str
    conn: socket

    def mpc_address(self):
        return "{id},{address},{port}".format(id=self.id, address=self.address, port=23000+self.id)


def run_server_role(id, address, num_parties):
    # log.info("Compiling All benchmarks")
    # compile_all_benchmarks()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((address, int(SERVER_PORT)))
    s.listen()
    server = Party(id=id, address=address, conn=None)
    log.info("Server started at address {} port {}. Server's MPC address is: {} ".format(
        address, SERVER_PORT, server.mpc_address()))
    ready_parties: dict[int, Party] = {server.id: server}
    while len(list(ready_parties.keys())) < num_parties:
        conn, ip_port_pair = s.accept()
        conn.settimeout(CONNECTION_TIMEOUT)
        msg = read_message(conn)
        if not msg:
            log.error("Unable to read message from the client.")
            conn.close()
            break

        if isinstance(msg, PartyReadyReq):
            party = Party(id=msg.id, address=ip_port_pair[0], conn=conn)
            log.info("Party {} is ready".format(party.mpc_address()))
            ready_parties[msg.id] = party
        else:
            log.error("Invalid message from {}".format(ip_port_pair))

    log.info("All parties are now ready...")
    mpc_addresses = [p.mpc_address() for p in list(ready_parties.values())]

    all_stats = []
    for test_case_dir in os.scandir(test_context.STAGES_DIR):
        if test_case_dir.name in test_context.SKIPPED_TESTS:
            continue

        all_args, non_vec_up_to = get_inputs(test_case_dir.name)
        if len(all_args) == 0:
            continue

        task_stats = StatsForTask(test_case_dir.name, [])

        i = 0
        for args in all_args:
            log.info("\n{} - arguments: {}".format(test_case_dir.name, args.args))

            protocol_stats: list[list[BenchmarkOutput]] = []
            target_protocols = [GMW_PROTOCOL, BMR_PROTOCOL]
            if test_case_dir.name == "inner_product":
                target_protocols.append("ArithmeticGmw")
            for protocol in target_protocols:
                for vectorized in [False, True]:
                    if i > non_vec_up_to and vectorized is False:
                        blank_output = [None] * num_parties
                        protocol_stats.append(blank_output)
                        continue

                    accumulated_output: dict[int, BenchmarkOutput] = {}
                    for j in range(NUM_ITERS):
                        log.info(
                            "Running Iteration {} {} {} {} {}".format(j + 1, test_case_dir.name, protocol,
                                                                      ("vec" if vectorized else "non-vec"),
                                                                      args.label))
                        request = RunBenchmarkReq(
                            party_addrs=mpc_addresses,
                            cmd_args=args.args,
                            benchmark_name=test_case_dir.name,
                            protocol=protocol,
                            vectorized=vectorized
                        )

                        # Ask everyone to run the benchmark
                        for p in ready_parties.values():
                            if p.id == server.id:
                                continue
                            write_message(p.conn, request)

                        # run it on this machine too
                        outputs: dict[int, BenchmarkOutput] = {
                            server.id: run_benchmark_for_party(
                                str(server.id), mpc_addresses, test_case_dir.name,
                                test_case_dir.path, protocol, vectorized, None, args.args)
                        }

                        # collect outputs
                        for p in ready_parties.values():
                            if p.id == server.id:
                                continue
                            outputs[p.id] = read_message(p.conn)

                        # no party should return blank output
                        no_output_parties = [k for k in outputs.keys() if outputs[k] is None]
                        if len(no_output_parties) > 0:
                            log.error("Run Failed! IDs {} returned no output".format(no_output_parties))
                            continue
                        log.info("Output {}".format(outputs[server.id].output.strip()))

                        # verify output is correct
                        for k in outputs.keys():
                            if k == server.id:
                                continue
                            assert outputs[server.id].output.strip() == outputs[k].output.strip(), \
                                (outputs[server.id].output.strip(), outputs[k].output.strip())

                        for k in outputs.keys():
                            if k in accumulated_output:
                                accumulated_output[k] = \
                                    BenchmarkOutput.by_accumulating_readings(outputs[k], accumulated_output[k])
                            else:
                                accumulated_output[k] = outputs[k]

                    protocol_stats.append(list(accumulated_output.values()))

            gmw = protocol_stats[0]
            gmw_vec = protocol_stats[1]
            bmr = protocol_stats[2]
            bmr_vec = protocol_stats[3]

            if gmw[0] is None and gmw_vec[0] is None and bmr[0] is None and bmr_vec[0] is None:
                log.warning("{}, {} No version ran on this iteration.".format(test_case_dir.name,
                                                                              args.label))
            else:
                if len(protocol_stats) == 6:
                    input_stats = StatsForInputConfig(label=args.label, gmw=gmw, gmw_vec=gmw_vec, bmr=bmr,
                                                      bmr_vec=bmr_vec, arith=protocol_stats[4],
                                                      arith_vec=protocol_stats[5])
                else:
                    input_stats = StatsForInputConfig(label=args.label, gmw=gmw, gmw_vec=gmw_vec, bmr=bmr,
                                                      bmr_vec=bmr_vec)
                update_benchmark_json(task_stats=task_stats, input_stats=input_stats)

            i += 1

        all_stats.append(task_stats)
        log.info("task {} DONE".format(task_stats.label))
    all_stats.append(task_stats)
    for p in ready_parties.values():
        if p.id == server.id:
            continue
        p.conn.close()
    print_benchmark_data(all_stats)


def run_client_role(myid, address):
    # log.info("Compiling All benchmarks")
    # compile_all_benchmarks()
    log.info("Client started, will connect to server at address {} port {}".format(address, SERVER_PORT))
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.connect((address, SERVER_PORT))
    server_sock.settimeout(CONNECTION_TIMEOUT)
    write_message(server_sock, PartyReadyReq(id=myid))
    while True:
        msg = read_message(server_sock)
        if isinstance(msg, RunBenchmarkReq):
            log.info("Request to run: {} {} {}".format(msg.benchmark_name, msg.protocol, msg.vectorized))
            for dir in os.scandir(test_context.STAGES_DIR):
                if dir.name == msg.benchmark_name:
                    test_case_dir = dir
                    break
            log.info("path is {}".format(test_case_dir.path))
            resp = run_benchmark_for_party(
                str(myid), msg.party_addrs, test_case_dir.name,
                test_case_dir.path, msg.protocol, msg.vectorized, None, msg.cmd_args
            )
            write_message(server_sock, resp)
        elif msg is None:
            log.info("Server closed connection!")
            break
        else:
            log.error("Invalid message from the server: {}".format(msg))
            break


def get_x_label_for_benchmark(name):
    if name == "biometric":
        return "Biometric Matching"
    if name == "biometric_fast":
        return "Biometric Matching (Fast)"
    if name == "convex_hull":
        return "Convex Hull"
    if name == "count_102":
        return "Count 102"
    if name == "count_123":
        return "Count 123"
    if name == "count_10s":
        return "Count 10s"
    if name == "cryptonets_max_pooling":
        return "Cryptonets (Max Pooling)"
    if name == "db_cross_join_trivial":
        return "Database Join"
    if name == "db_variance":
        return "Database Variance"
    if name == "histogram":
        return "Histogram"
    if name == "inner_product":
        return "Inner Product"
    if name == "kmeans_iteration":
        return "k-means"
    if name == "longest_102":
        return "Longest 102"
    if name == "longest_odd_10":
        return "Longest Odd 10"
    if name == "max_dist_between_syms":
        return "Max. Dist. b/w Symbols"
    if name == "max_sum_between_syms":
        return "Max. Sum b/w Symbols"
    if name == "minimal_points":
        return "Minimal Points"
    if name == "mnist_relu":
        return "MNIST ReLU"
    if name == "psi":
        return "Private Set Intersection"

    return name

def run_gnuplot(plot_script, data_file, graph_file, title, y_label, dir, other_args = []):
    log.info("gnuplot -c '{}' '{}' '{}' \"{}\" \"{}\" {}".format(plot_script,
        data_file, graph_file, title, y_label, other_args)
    )

    subprocess.run(
            ["gnuplot", "-c", plot_script, data_file, graph_file, title, y_label] + other_args,
            cwd=dir,
            check=True,
        )

def ratio(a, b):
    if b != 0:
        return a/b
    return 0


def generate_graph_for_attr(all_stats, get_val, get_sd, y_label, dir, party_index):
    y_label_simple = ''.join(c for c in y_label if c.isalnum())
    for task_stat in all_stats:
        fname = "{}-p{}-{}.txt".format(task_stat.label, party_index, y_label_simple)
        hist_graph_file = "{}-hist-p{}-{}{}".format(task_stat.label, party_index, y_label_simple, GRAPH_EXT)
        line_graph_file = "{}-line-p{}-{}{}".format(task_stat.label, party_index, y_label_simple, GRAPH_EXT)
        file_path = os.path.join(dir, fname)
        with open(file_path, mode='w', encoding='utf-8') as f:
            line = '\t'.join(['x',
                '"Benchmark"',
                '"GMW"',
                '"GMW (Vectorized)"',
                '"BMR"',
                '"BMR (Vectorized)"',
                '"GMW Improvement"',
                '"BMR Improvement"'])
            if get_sd is not None:
                line = '\t'.join(['x',
                    '"Benchmark"',
                    '"GMW"',
                    '"SD"',
                    '"GMW (Vectorized)"',
                    '"SD"',
                    '"BMR"',
                    '"SD"',
                    '"BMR (Vectorized)"',
                    '"SD"',
                    '"GMW Improvement"',
                    '"BMR Improvement"'])
            f.write(line + "\n")
            x = 1
            for i in task_stat.input_configs:
                label = i.label
                if task_stat.label.startswith('biometric'):
                    parts = label.split(", ")
                    label = parts[1]


                nv_gmw = get_val(i.gmw[party_index])
                v_gmw  = get_val(i.gmw_vec[party_index])
                r_gmw  = ratio(nv_gmw, v_gmw)

                nv_bmr = get_val(i.bmr[party_index])
                v_bmr  = get_val(i.bmr_vec[party_index])
                r_bmr  = ratio(nv_bmr, v_bmr)

                vals = [x, '"' + label + '"',
                        nv_gmw, v_gmw,
                        nv_bmr, v_bmr,
                        r_gmw, r_bmr]

                if get_sd is not None:
                    nv_gmw_sd = get_sd(i.gmw[party_index])
                    v_gmw_sd = get_sd(i.gmw_vec[party_index])
                    nv_bmr_sd = get_sd(i.bmr[party_index])
                    v_bmr_sd = get_sd(i.bmr_vec[party_index])

                    vals = [x, '"' + label + '"',
                        nv_gmw, nv_gmw_sd, v_gmw, v_gmw_sd,
                        nv_bmr, nv_bmr_sd, v_bmr, v_bmr_sd,
                        r_gmw, r_bmr]

                line = '\t'.join(list(map(str, vals))) + "\n"

                f.write(line)
                x += 1

        title = task_stat.label
        hist_script = os.path.join(FILE_DIR, 'plt_histogram.gnu')
        if get_sd is not None:
            hist_script = os.path.join(FILE_DIR, 'plt_histogram_with_errorbars.gnu')
        line_script = os.path.join(FILE_DIR, 'plt_linegraph.gnu')
        run_gnuplot(hist_script, file_path, hist_graph_file, task_stat.label,
            y_label, dir, other_args = [])
        # run_gnuplot(line_script, file_path, line_graph_file, task_stat.label, 
        #     y_label, dir, other_args = [])

def generate_cumulative_graph_for_attr(all_stats, get_val, get_sd, y_label, dir, party_index):
    y_label_simple = ''.join(c for c in y_label if c.isalnum())
    fname = "all-p{}-{}.txt".format(party_index, y_label_simple)
    hist_graph_file = "all-hist-p{}-{}{}".format(party_index, y_label_simple, GRAPH_EXT)
    line_graph_file = "all-line-p{}-{}{}".format(party_index, y_label_simple, GRAPH_EXT)
    file_path = os.path.join(dir, fname)
    with open(file_path, mode='w', encoding='utf-8') as f:
        line = '\t'.join(['x',
                '"Benchmark"',
                '"GMW"',
                '"GMW (Vectorized)"',
                '"BMR"',
                '"BMR (Vectorized)"',
                '"GMW Improvement"',
                '"BMR Improvement"'])
        if get_sd is not None:
            line = '\t'.join(['x',
                '"Benchmark"',
                '"GMW"',
                '"SD"',
                '"GMW (Vectorized)"',
                '"SD"',
                '"BMR"',
                '"SD"',
                '"BMR (Vectorized)"',
                '"SD"',
                '"GMW Improvement"',
                '"BMR Improvement"'])
        f.write(line + "\n")
        x = 1
        for task_stat in all_stats:
            label = get_x_label_for_benchmark(task_stat.label)
            for i in range(len(task_stat.input_configs)-1, -1, -1):
                input = task_stat.input_configs[i]
                if input.gmw[party_index] is not None and input.gmw_vec[party_index] is not None and \
                    input.bmr[party_index] is not None and input.bmr_vec[party_index] is not None:
                    nv_gmw = get_val(input.gmw[party_index])
                    v_gmw  = get_val(input.gmw_vec[party_index])
                    r_gmw  = ratio(nv_gmw, v_gmw)

                    nv_bmr = get_val(input.bmr[party_index])
                    v_bmr  = get_val(input.bmr_vec[party_index])
                    r_bmr  = ratio(nv_bmr, v_bmr)

                    vals = [x, '"' + label + '"',
                        nv_gmw, v_gmw,
                        nv_bmr, v_bmr,
                        r_gmw, r_bmr]

                    if get_sd is not None:
                        nv_gmw_sd = get_sd(input.gmw[party_index])
                        v_gmw_sd = get_sd(input.gmw_vec[party_index])
                        nv_bmr_sd = get_sd(input.bmr[party_index])
                        v_bmr_sd = get_sd(input.bmr_vec[party_index])

                        vals = [x, '"' + label + '"',
                            nv_gmw, nv_gmw_sd, v_gmw, v_gmw_sd,
                            nv_bmr, nv_bmr_sd, v_bmr, v_bmr_sd,
                            r_gmw, r_bmr]

                    line = '\t'.join(list(map(str, vals))) + "\n"
                    #f.write("{x}\t\"{label}\"\t{nv_gmw}\t{v_gmw}\t{nv_bmr}\t{v_bmr}\t{r_gmw}\t{r_bmr}\n".format(
                    #    x=x, label=label, nv_gmw=nv_gmw, v_gmw=v_gmw, r_gmw=r_gmw, nv_bmr=nv_bmr, v_bmr=v_bmr, 
                    #    r_bmr=r_bmr))
                    f.write(line)
                    x += 1
                    break

    title = "{} - All Benchmarks".format(y_label)
    hist_script = os.path.join(FILE_DIR, 'plt_all_histogram.gnu')
    if get_sd is not None:
        hist_script = os.path.join(FILE_DIR, 'plt_all_histogram_with_errorbars.gnu')
    # line_script = os.path.join(FILE_DIR, 'plt_linegraph.gnu')
    run_gnuplot(hist_script, file_path, hist_graph_file, title, y_label, dir, other_args = [])
    # run_gnuplot(line_script, file_path, line_graph_file, title, y_label, dir, other_args = [])


def generate_single_network_graphs(all_stats, dir, party_index):
    log.info("generating graphs for {} benchmarks in {}".format(len(all_stats), dir))

    get_num_gates = lambda x: x.circuit_stats.num_gates if x is not None else 0
    generate_graph_for_attr(all_stats, get_num_gates, None, 'Total Gates', dir, party_index)
    generate_cumulative_graph_for_attr(all_stats, get_num_gates, None, 'Total Gates', dir, party_index)

    get_circ_gen_time = lambda x: (x.circuit_stats.circuit_gen_time/1000) if x is not None else 0
    generate_graph_for_attr(all_stats, get_circ_gen_time, None, 'Circuit Generation Time (sec)', dir, party_index)
    generate_cumulative_graph_for_attr(all_stats, get_circ_gen_time, None, 'Circuit Generation Time (sec)', dir,
                                       party_index)

    get_online_time = lambda x: (x.timing_stats.gates_online.mean/1000) if x is not None else 0
    get_online_time_sd = lambda x: (x.timing_stats.gates_online.stddev/1000) if x is not None else 0
    generate_graph_for_attr(all_stats, get_online_time, get_online_time_sd, 'Online Time (sec)', dir, party_index)
    generate_cumulative_graph_for_attr(all_stats, get_online_time, get_online_time_sd, 'Online Time (sec)', dir,
                                       party_index)

    get_setup_time = lambda x: ((x.timing_stats.gates_setup.mean + x.timing_stats.preprocess_total.mean)/1000) if x is not None else 0
    get_setup_time_sd = lambda x: ((x.timing_stats.gates_setup.stddev + x.timing_stats.preprocess_total.stddev)/1000) if x is not None else 0
    generate_graph_for_attr(all_stats, get_setup_time, get_setup_time_sd, 'Setup Time (sec)', dir, party_index)
    generate_cumulative_graph_for_attr(all_stats, get_setup_time, get_setup_time_sd, 'Setup Time (sec)', dir,
                                       party_index)

    get_eval_time = lambda x: (x.timing_stats.circuit_evaluation.mean/1000) if x is not None else 0
    get_eval_time_sd = lambda x: (x.timing_stats.circuit_evaluation.stddev/1000) if x is not None else 0
    generate_graph_for_attr(all_stats, get_eval_time, get_eval_time_sd, 'Online + Setup Time (sec)', dir, party_index)
    generate_cumulative_graph_for_attr(all_stats, get_eval_time, get_eval_time_sd, 'Online + Setup Time (sec)', dir,
                                       party_index)

    get_send_size = lambda x: x.timing_stats.communication.send_size if x is not None else 0
    generate_graph_for_attr(all_stats, get_send_size, None, 'Communication (MiB)', dir, party_index)
    generate_cumulative_graph_for_attr(all_stats, get_send_size, None, 'Communication (MiB)', dir, party_index)

    # Not needed
    # get_recv_size = lambda x: x.timing_stats.communication.recv_size if x is not None else 0
    # generate_graph_for_attr(all_stats, get_recv_size, 'Received Data (MiB)', dir)  
    # generate_cumulative_graph_for_attr(all_stats, get_recv_size, 'Received Data (MiB)', dir)


def get_benchmark_stats(all_stats, benchmark_name, input_label, party_index):
    for task_stat in all_stats:
        if task_stat.label == benchmark_name:
            for i in range(len(task_stat.input_configs)-1, -1, -1):
                input = task_stat.input_configs[i]
                if input.label == input_label:
                    if input.gmw_vec[party_index] is not None and input.bmr_vec[party_index] is not None:
                        return input
    return None

def generate_comparison_graphs(lan_stats, wan_stats, get_val, y_label, dir, party_index):
    y_label_simple = ''.join(c for c in y_label if c.isalnum())
    data_file = "comparison-p{}-{}.txt".format(party_index, y_label_simple)
    graph_file = "comparison-hist-p{}-{}{}".format(party_index, y_label_simple, GRAPH_EXT)
    # line_graph_file = "all-line {}{}".format(y_label, GRAPH_EXT)
    data_file_path = os.path.join(dir, data_file)
    with open(data_file_path, mode='w', encoding='utf-8') as f:
        line = '\t'.join(['x', '"Benchmark"', '"GMW LAN"', '"GMW WAN"',
            '"BMR LAN"', '"BMR WAN"', '"Input Label"']) + '\n'
        # f.write("x\tBenchmark\t\"LAN\"\t\"WAN\"\tWAN/LAN\tInputLabel\n")
        f.write(line)
        x = 1
        for lan_task_stat in lan_stats:
            label = get_x_label_for_benchmark(lan_task_stat.label)

            for i in range(len(lan_task_stat.input_configs)-1, -1, -1):
                lan_input = lan_task_stat.input_configs[i]
                if lan_input.gmw_vec[party_index] is not None and lan_input.bmr_vec[party_index] is not None:
                    wan_input = get_benchmark_stats(wan_stats, lan_task_stat.label, lan_input.label, party_index)
                    if wan_input is not None:
                        gmw_lan = get_val(lan_input.gmw_vec[party_index])
                        gmw_wan  = get_val(wan_input.gmw_vec[party_index])
                        bmr_lan = get_val(lan_input.bmr_vec[party_index])
                        bmr_wan  = get_val(wan_input.bmr_vec[party_index])

                        vals = list(
                            map(str,
                                [x, '"' + label + '"', gmw_lan, gmw_wan, bmr_lan, bmr_wan, '"' + lan_input.label + '"']
                                )
                        )

                        line = '\t'.join(vals) + '\n'

                        # gmwf.write("{x}\t\"{label}\"\t{lan}\t{wan}\t{r_wan_lan}\t\"{input_label}\"\n".format(
                        #     x=x, label=label, lan=lan, wan=wan, r_wan_lan=r_wan_lan, 
                        #     input_label=lan_input.label))
                        f.write(line)
                        break


    title = "{} - All Benchmarks".format(y_label)
    hist_script = os.path.join(FILE_DIR, 'plt_comparison_histogram.gnu')
    # line_script = os.path.join(FILE_DIR, 'plt_linegraph.gnu')
    run_gnuplot(hist_script, data_file_path, graph_file, title, y_label, dir, other_args = [])
    # run_gnuplot(hist_script, bmrfile_path, bmr_hist_graph_file, bmr_title, y_label, dir, other_args = [])
    # run_gnuplot(line_script, file_path, line_graph_file, title, y_label, dir, other_args = [])

def gen_latex_table(all_stats, party_index):
    print('\n\n')
    for task_stats in all_stats:
        if(task_stats.label == 'biometric_fast'):
            continue
        label = get_x_label_for_benchmark(task_stats.label)
        for i in range(len(task_stats.input_configs)-1, -1, -1):
            input = task_stats.input_configs[i]
            if input.gmw[party_index] is not None and input.gmw_vec[party_index] is not None and \
                input.bmr[party_index] is not None and input.bmr_vec[party_index] is not None:

                a_ts = input.gmw[party_index].timing_stats
                a_cs = input.gmw[party_index].circuit_stats
                b_ts = input.bmr[party_index].timing_stats
                b_cs = input.bmr[party_index].circuit_stats

                vals1 = [label,
                  "{:,.0f}".format(round(a_ts.gates_online.mean/1000)),
                  "{:,.0f}".format(round((a_ts.preprocess_total.mean + a_ts.gates_setup.mean)/1000)),
                  "{:,.0f}".format(round(a_cs.num_gates/1000)),
                  "{:,.0f}".format(round(a_cs.circuit_gen_time/1000)),
                  "{:,.0f}".format(round(a_ts.communication.send_num_msgs/1000)),
                  "{:,}".format(round(a_ts.communication.send_size)),

                  "{:,.0f}".format(round(b_ts.gates_online.mean/1000)),
                  "{:,.0f}".format(round((b_ts.preprocess_total.mean + b_ts.gates_setup.mean)/1000)),
                  "{:,.0f}".format(round(b_cs.num_gates/1000)),
                  "{:,.0f}".format(round(b_cs.circuit_gen_time/1000)),
                  "{:,.0f}".format(round(b_ts.communication.send_num_msgs/1000)),
                  "{:,}".format(round(b_ts.communication.send_size))
                ]


                c_ts = input.gmw_vec[party_index].timing_stats
                c_cs = input.gmw_vec[party_index].circuit_stats
                d_ts = input.bmr_vec[party_index].timing_stats
                d_cs = input.bmr_vec[party_index].circuit_stats

                vals2 = [label + " (V)",
                  "{:,.0f}".format(round(c_ts.gates_online.mean/1000)),
                  "{:,.0f}".format(round((c_ts.preprocess_total.mean + c_ts.gates_setup.mean)/1000)),
                  "{:,.0f}".format(round(c_cs.num_gates/1000)),
                  "{:,.0f}".format(round(c_cs.circuit_gen_time/1000)),
                  "{:,.0f}".format(round(c_ts.communication.send_num_msgs/1000)),
                  "{:,}".format(round(c_ts.communication.send_size)),

                  "{:,.0f}".format(round(d_ts.gates_online.mean/1000)),
                  "{:,.0f}".format(round((d_ts.preprocess_total.mean + d_ts.gates_setup.mean)/1000)),
                  "{:,.0f}".format(round(d_cs.num_gates/1000)),
                  "{:,.0f}".format(round(d_cs.circuit_gen_time/1000)),
                  "{:,.0f}".format(round(d_ts.communication.send_num_msgs/1000)),
                  "{:,}".format(round(d_ts.communication.send_size))
                ]

                line = ' & '.join(list(map(str, vals1))) + '\\\\'
                print(line)
                line = ' & '.join(list(map(str, vals2))) + '\\\\'
                print(line)
                print('\\midrule')
                break


def generate_graphs(lan, wan, party_index):
    if lan is not True and wan is not True:
        log.error("Need to specify at least one of LAN or WAN directories for source data")
        return

    log.info("LAN dir: {}".format(LAN_DIR))
    log.info("WAN dir: {}".format(WAN_DIR))

    lan_files = [os.path.join(LAN_DIR, f) for f in os.listdir(LAN_DIR) if \
        os.path.isfile(os.path.join(LAN_DIR, f)) and f.endswith('.json')]
    wan_files = [os.path.join(WAN_DIR, f) for f in os.listdir(WAN_DIR) if \
        os.path.isfile(os.path.join(WAN_DIR, f)) and f.endswith('.json')]

    lan_files = sorted(lan_files)
    wan_files = sorted(wan_files)
    lan_stats = []
    wan_stats = []

    if lan is True:
        for f in lan_files:
            if "biometric_fast" in f:
                continue
            with open(f, "r", encoding='utf-8') as f:
                json_str = f.read()
                file_stats = json_deserialize(json_str)
                lan_stats.append(file_stats)
        # gen_latex_table(lan_stats, party_index=0)
        generate_single_network_graphs(lan_stats, LAN_GRAPHS_DIR, party_index)

    if wan is True:
        for f in wan_files:
            if "biometric_fast" in f:
                continue
            with open(f, "r", encoding='utf-8') as f:
                json_str = f.read()
                file_stats = json_deserialize(json_str)
                wan_stats.append(file_stats)
        generate_single_network_graphs(wan_stats, WAN_GRAPHS_DIR, party_index)

    if lan is True and wan is True:
        get_num_gates = lambda x: x.circuit_stats.num_gates if x is not None else 0
        generate_comparison_graphs(lan_stats, wan_stats, get_num_gates, 'Total Gates',
            COMPARISON_GRAPHS_DIR, party_index)

        get_circ_gen_time = lambda x: int(x.circuit_stats.circuit_gen_time/1000) if x is not None else 0
        generate_comparison_graphs(lan_stats, wan_stats, get_circ_gen_time,
            'Circuit Generation Time (sec)', COMPARISON_GRAPHS_DIR, party_index)

        get_online_time = lambda x: int(x.timing_stats.circuit_evaluation.mean/1000) if x is not None else 0
        generate_comparison_graphs(lan_stats, wan_stats, get_online_time, 'Online + Setup Time (sec)',
            COMPARISON_GRAPHS_DIR, party_index)

        get_online_time = lambda x: int(x.timing_stats.gates_online.mean/1000) if x is not None else 0
        generate_comparison_graphs(lan_stats, wan_stats, get_online_time, 'Online Time (sec)',
            COMPARISON_GRAPHS_DIR, party_index)

        get_setup_time = lambda x: int((x.timing_stats.gates_setup.mean+x.timing_stats.preprocess_total.mean)/1000) if x is not None else 0
        generate_comparison_graphs(lan_stats, wan_stats, get_setup_time, 'Setup Time (sec)',
            COMPARISON_GRAPHS_DIR, party_index)

        get_send_size = lambda x: x.timing_stats.communication.send_size if x is not None else 0
        generate_comparison_graphs(lan_stats, wan_stats, get_send_size, 'Communication (MiB)',
            COMPARISON_GRAPHS_DIR, party_index)

        # get_recv_size = lambda x: x.timing_stats.communication.recv_size if x is not None else 0
        # generate_comparison_graphs(lan_stats, wan_stats, get_recv_size, 'Received Data (MiB)',
        #     COMPARISON_GRAPHS_DIR)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="runs and collects benchmarks statistics for the paper. (assumes correct network config)")
    parser.add_argument('-i', '--id', type=int,
                        help="id of the party e.g. 0, 1, 2, 3 ... party 0 acts as server to collect stats"
                        )
    parser.add_argument('-n', '--num_parties', type=int, help="number of parties, an integer > 1",
                        )
    parser.add_argument('-a', '--address', help="party 0 address",
                        )

    parser.add_argument('-g', "--graphs",
        action="store_true",
        help="generates graphs from benchmarks",
    )
    parser.add_argument('-l', '--lan',
        action="store_true",
        help="only used when generating graphs, uses LAN data",
    )
    parser.add_argument('-w', '--wan',
        action="store_true",
        help="only used when generating graphs, uses WAN data",
    )

    parser.add_argument('-c', '--compile',
        action="store_true",
        help="compile all benchmarks",
    )

    parser.add_argument('-p', '--party_index', type=int, default=0,
                        help="index of the party to generate graphs for (default=0)",
                        )

    args = parser.parse_args()

    if args.graphs:
        generate_graphs(args.lan, args.wan, args.party_index)
    elif args.compile:
        compile_all_benchmarks()
    else:
        log.info("ID: {} NUM_PARTIES: {} ADDRESS: {}".format(args.id, args.num_parties, args.address))
        if args.id == 0:
            run_server_role(args.id, args.address, args.num_parties)
        else:
            run_client_role(args.id, args.address)

        # if args.role == 'b':
        #     run_paper_benchmarks()
        # elif args.role == 's':
        #     run_server_role(args.address)
        # else:
        #     run_client_role(args.address)
