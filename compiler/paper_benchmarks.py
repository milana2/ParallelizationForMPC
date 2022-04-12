
from argparse import ArgumentParser
from dataclasses import dataclass
import os
import sys
import subprocess

import logging
import logging.handlers
import random
import json

import compiler

from tests import context as test_context
from tests.benchmark import run_benchmark

from utils import json_serialize, json_deserialize, StatsForInputConfig, StatsForTask

GMW_PROTOCOL = "BooleanGmw"
BMR_PROTOCOL = "Bmr"

FILE_DIR = os.path.dirname(__file__)
BENCHDATA_DIR = os.path.join(FILE_DIR, "benchdata")
LAN_DIR = os.path.join(BENCHDATA_DIR, "lan")
LAN_GRAPHS_DIR = os.path.join(LAN_DIR, "graphs")
WAN_DIR = os.path.join(BENCHDATA_DIR, "wan")
WAN_GRAPHS_DIR = os.path.join(WAN_DIR, "graphs")
COMPARISON_GRAPHS_DIR = os.path.join(BENCHDATA_DIR, "comparison-graphs")
GRAPH_EXT = ".png"

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
log.addHandler(console);

@dataclass
class InputArgs:
    label: str
    args: list[str]


random.seed(0) # Intentionally seeding with a known value, for reproducibility
def get_rand_ints(n, min=1, max=100):
    return [random.randint(min, max) for i in range(n)]

def get_biometric_inputs() -> tuple[list[InputArgs], int]:
    all_args = []
    non_vec_up_to = 6 # Only run non-vectorized benchmark upto this index
    for config in [[4, 4], [4, 8], [4, 16], [4, 32], [4, 64], [4, 128], [4, 256], [4, 512], [4, 1024], [4, 4096]]:
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

def get_convex_hull_inputs():
    all_args = []
    non_vec_up_to = 100
    for N in [4, 8, 16, 32, 64, 128, 256, 512, 1024, 4096]:
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
    non_vec_up_to = 100
    for N in [8, 16, 32, 64, 128, 256, 512, 1024, 4096]:
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
    non_vec_up_to = 100
    for N in [8, 16, 32, 64, 128, 256, 512, 1024, 4096]:
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
    non_vec_up_to = 100
    for N in [8, 16, 32, 64, 128, 256, 512, 1024, 4096]:
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

def get_db_variance_inputs():
    all_args = []
    non_vec_up_to = 100
    for N in [8, 16, 32, 64, 128, 256, 512, 1024, 4096]:
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
    non_vec_up_to = 100
    for N in [8, 16, 32, 64, 128, 256, 512, 1024, 4096]:
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
    non_vec_up_to = 8
    for N in [4, 8, 16, 32, 64, 128, 256, 512, 1024, 4096]:
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
    non_vec_up_to = 100
    for config in [[32, 5], [32, 8], [64, 8], [128, 8], [200, 5], [256, 8]]:
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

def get_max_dist_between_syms_inputs():
    all_args = []
    non_vec_up_to = 100
    for N in [8, 16, 32, 64, 128, 256, 512, 1024, 4096]:
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

def get_psi_inputs()-> tuple[list[InputArgs], int]:
    all_args = []
    non_vec_up_to = 6
    for config in [[16, 16], [32, 32], [64, 64], [128, 128], [256, 256], [512, 512], [1024, 1024]]:#[2048, 2084], [4096, 4096]]:
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
    return (all_args, non_vec_up_to)

def get_inputs(name: str) -> tuple[list[InputArgs], int]:
    # if name == "biometric" or name == "biometric_fast":
    #      return get_biometric_inputs()
    # if name == "convex_hull" or name == "minimal_points":
    #     return get_convex_hull_inputs()
    # if name == "count_102" or name == "longest_102":
    #     return get_count_102_inputs()
    # if name == "count_10s":
    #     return get_count_10s_inputs()
    # if name == "count_123":
    #     return get_count_123_inputs()
    # if name == "db_variance":
    #     return get_db_variance_inputs()
    if name == "histogram":
        return get_histogram_inputs()
    # if name == "inner_product":
    #     return get_inner_product_inputs()
    # if name == "kmeans_iteration":
    #     return get_kmeans_iteration_inputs()
    # if name == "max_dist_between_syms" or name == "max_sum_between_syms":
    #     return get_max_dist_between_syms_inputs()
    # if name == "psi": # segfaults right now
    #     return get_psi_inputs()
    return [[], 0]


def print_protocol_stats(p0, vec_p0, p1, vec_p1,):
    ts0 = cs0 = None
    if p0 is not None:
        ts0 = p0.timing_stats
        cs0 = p0.circuit_stats

    ts0v = cs0v = None
    if vec_p0 is not None:
        ts0v = vec_p0.timing_stats
        cs0v = vec_p0.circuit_stats
        
    ts1 = None
    if p1 is not None:
        ts1 = p1.timing_stats
    
    ts1v = vec_p1.timing_stats if vec_p1 is not None else None

    log.info("Timing/Communication")
    labels = ["Party 0 NonVec", "Party 0 Vectorized", "Party 1 NonVec", "Party 1 Vectorized"]
    j = 0
    for i in [ts0, ts0v, ts1, ts1v]:
        if i is None:
            j += 1
            continue

        log.info(labels[j])
        log.info("{} {} ms, {} {} ms, {} {} ms".format(i.preprocess_total.datapoint_name, 
            i.preprocess_total.mean, i.gates_setup.datapoint_name, i.gates_setup.mean,
            i.gates_online.datapoint_name, i.gates_online.mean))
        comm = i.communication
        log.info("Send: {} MiB ({} Msgs) - Recv: {} MiB ({} Msgs)".format(
            comm.send_size, comm.send_num_msgs, comm.recv_size, comm.recv_num_msgs))
        j += 1
    log.info("Circuit (Non-Vectorized vs Vectorized)")
    for i in [cs0, cs0v]:#, cs1, cs1v]: # circuit information should be identical for all parties
        if i is None:
            continue
        log.info("Num Gates: {} In: {}, Out: {}, SIMD: {}, Non-SIMD: {}, Circ-Gen-Time: {} ms".format(
            i.num_gates, i.num_inputs, i.num_outputs, i.num_simd_gates, i.num_nonsimd_gates, 
            i.circuit_gen_time))

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
            
            print_protocol_stats(v.gmw_p0, v.gmw_vec_p0,v.gmw_p1, v.gmw_vec_p1)

            log.info("-"*40)
            log.info("{} - BMR".format(v.label))
            log.info("-"*40)
            print_protocol_stats(v.bmr_p0, v.bmr_vec_p0, v.bmr_p1, v.bmr_vec_p1)


def run_paper_benchmarks():
    all_stats = []
    for test_case_dir in os.scandir(test_context.STAGES_DIR):
        if test_case_dir.name in test_context.SKIPPED_TESTS:
                continue

        all_args, non_vec_up_to = get_inputs(test_case_dir.name)
        if len(all_args) == 0:
            continue;

        task_stats = StatsForTask(test_case_dir.name, [])
        input_fname = os.path.join(test_case_dir.path, "input.py")

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
                input_stats = StatsForInputConfig(args.label, gmw_p0, gmw_p1, gmw_vec_p0, gmw_vec_p1,
                    bmr_p0, bmr_p1, bmr_vec_p0, bmr_vec_p1)
                task_stats.input_configs.append(input_stats)
                log.info("task {} input config {} DONE".format(task_stats.label, input_stats.label))

                file_path = os.path.join(FILE_DIR, "{}.json".format(task_stats.label))
                with open(file_path, "w", encoding='utf-8') as f:
                    json_str = json_serialize(task_stats)
                    f.write(json_str)
            
            i += 1

        all_stats.append(task_stats)
        log.info("task {} DONE".format(task_stats.label))
    print_benchmark_data(all_stats)


def get_x_label_for_benchmark(name):
    if name == "biometric":
        return "BioDist"
    if name == "biometric_fast":
        return "BioDistFast"
    if name == "convex_hull":
        return "ConvH"
    if name == "count_102":
        return "Count102"
    if name == "count_123":
        return "Count123"
    if name == "count_10s":
        return "Count10s"
    if name == "db_variance":
        return "DBVar"
    if name == "histogram":
        return "Hist"
    if name == "inner_product":
        return "InnerProd"
    if name == "kmeans_iteration":
        return "k-means"
    if name == "longest_102":
        return "Longest102"
    if name == "max_dist_between_syms":
        return "Dist/Syms"
    if name == "max_sum_between_syms":
        return "Sum/Syms"
    if name == "minimal_points":
        return "Min Points"
    if name == "psi":
        return "PSI"

    return name

def run_gnuplot(plot_script, data_file, graph_file, title, y_label, dir, other_args = []):
    log.info("gnuplot -c '{}' '{}' '{}' \"{}\" \"{}\" {}".format(plot_script, 
        data_file, graph_file, title, y_label, other_args)
    )

    with subprocess.Popen(
        [
            "gnuplot",
            "-c", plot_script,
            data_file, graph_file,
            title, y_label
        ] + other_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=dir
    ) as gnuplot:
        gnuplot.wait()
        if(gnuplot.returncode != 0):
            log.error("gnuplot exited with returncode: {0}".format(gnuplot.returncode))
            log.error("stderr: \n{0}".format(gnuplot.stderr.read()))
            log.debug("stdout: \n{0}".format(gnuplot.stdout.read()))
            exit(1)

def ratio(a, b):
    if b != 0:
        return a/b
    return 0


def generate_graph_for_attr(all_stats, get_val, y_label, dir):
    for task_stat in all_stats:
        fname = "{}-{}.txt".format(task_stat.label, y_label)
        hist_graph_file = "{}-hist {}{}".format(task_stat.label, y_label, GRAPH_EXT)
        line_graph_file = "{}-line {}{}".format(task_stat.label, y_label, GRAPH_EXT)
        file_path = os.path.join(dir, fname)
        with open(file_path, mode='w', encoding='utf-8') as f:
            f.write("x\tInput\t\"GMW\"\t\"GMW (Vectorized)\"\t\"BMR\"" \
                "\t\"BMR (Vectorized)\"\t\"GMW Improvement\"\t\"BMR Improvement\"\n")
            x = 1
            for i in task_stat.input_configs:
                label = i.label
                if task_stat.label.startswith('biometric'):
                    parts = label.split(", ")
                    label = parts[1]


                nv_gmw = get_val(i.gmw_p0)
                v_gmw  = get_val(i.gmw_vec_p0)
                r_gmw  = ratio(nv_gmw, v_gmw)

                nv_bmr = get_val(i.bmr_p0)
                v_bmr  = get_val(i.bmr_vec_p0)
                r_bmr  = ratio(nv_bmr, v_bmr)

                f.write("{x}\t\"{label}\"\t{nv_gmw}\t{v_gmw}\t{nv_bmr}\t{v_bmr}\t{r_gmw}\t{r_bmr}\n".format(
                    x=x, label=label, nv_gmw=nv_gmw, v_gmw=v_gmw, r_gmw=r_gmw, nv_bmr=nv_bmr, v_bmr=v_bmr, 
                    r_bmr=r_bmr))
                x += 1

        title = task_stat.label
        hist_script = os.path.join(FILE_DIR, 'plt_histogram.gnu')
        line_script = os.path.join(FILE_DIR, 'plt_linegraph.gnu')
        run_gnuplot(hist_script, file_path, hist_graph_file, task_stat.label, 
            y_label, dir, other_args = [])
        # run_gnuplot(line_script, file_path, line_graph_file, task_stat.label, 
        #     y_label, dir, other_args = [])

def generate_cumulative_graph_for_attr(all_stats, get_val, y_label, dir):
    fname = "all-{}.txt".format(y_label)
    hist_graph_file = "all-hist {}{}".format(y_label, GRAPH_EXT)
    line_graph_file = "all-line {}{}".format(y_label, GRAPH_EXT)
    file_path = os.path.join(dir, fname)
    with open(file_path, mode='w', encoding='utf-8') as f:
        f.write("x\tBenchmark\t\"GMW\"\t\"GMW (Vectorized)\"\t\"BMR\"" \
                "\t\"BMR (Vectorized)\"\t\"GMW Improvement\"\t\"BMR Improvement\"\n")
        x = 1
        for task_stat in all_stats:
            label = get_x_label_for_benchmark(task_stat.label)
            for i in range(len(task_stat.input_configs)-1, 0, -1):
                input = task_stat.input_configs[i]
                if input.gmw_p0 is not None and input.gmw_vec_p0 is not None and \
                    input.bmr_p0 is not None and input.bmr_vec_p0 is not None:
                    nv_gmw = get_val(input.gmw_p0)
                    v_gmw  = get_val(input.gmw_vec_p0)
                    r_gmw  = ratio(nv_gmw, v_gmw)

                    nv_bmr = get_val(input.bmr_p0)
                    v_bmr  = get_val(input.bmr_vec_p0)
                    r_bmr  = ratio(nv_bmr, v_bmr)
                    f.write("{x}\t\"{label}\"\t{nv_gmw}\t{v_gmw}\t{nv_bmr}\t{v_bmr}\t{r_gmw}\t{r_bmr}\n".format(
                        x=x, label=label, nv_gmw=nv_gmw, v_gmw=v_gmw, r_gmw=r_gmw, nv_bmr=nv_bmr, v_bmr=v_bmr, 
                        r_bmr=r_bmr))
                    x += 1
                    break

    title = "{} - All Benchmarks".format(y_label)            
    hist_script = os.path.join(FILE_DIR, 'plt_all_histogram.gnu')
    # line_script = os.path.join(FILE_DIR, 'plt_linegraph.gnu')
    run_gnuplot(hist_script, file_path, hist_graph_file, title, y_label, dir, other_args = [])
    # run_gnuplot(line_script, file_path, line_graph_file, title, y_label, dir, other_args = [])


def generate_single_network_graphs(all_stats, dir):
    log.info("generating graphs for {} benchmarks in {}".format(len(all_stats), dir))

    get_num_gates = lambda x: x.circuit_stats.num_gates if x is not None else 0
    generate_graph_for_attr(all_stats, get_num_gates, 'Total Gates', dir)
    generate_cumulative_graph_for_attr(all_stats, get_num_gates, 'Total Gates', dir)
    
    get_circ_gen_time = lambda x: x.circuit_stats.circuit_gen_time if x is not None else 0
    generate_graph_for_attr(all_stats, get_circ_gen_time, 'Circuit Generation Time (ms)', dir)
    generate_cumulative_graph_for_attr(all_stats, get_circ_gen_time, 'Circuit Generation Time (ms)', dir)
    
    get_online_time = lambda x: x.timing_stats.gates_online.mean if x is not None else 0
    generate_graph_for_attr(all_stats, get_online_time, 'Online Time (ms)', dir)  
    generate_cumulative_graph_for_attr(all_stats, get_online_time, 'Online Time (ms)', dir)

    get_setup_time = lambda x: x.timing_stats.gates_setup.mean if x is not None else 0
    generate_graph_for_attr(all_stats, get_setup_time, 'Setup Time (ms)', dir)    
    generate_cumulative_graph_for_attr(all_stats, get_setup_time, 'Setup Time (ms)', dir)

    get_send_size = lambda x: x.timing_stats.communication.send_size if x is not None else 0
    generate_graph_for_attr(all_stats, get_send_size, 'Sent Data (MiB)', dir)
    generate_cumulative_graph_for_attr(all_stats, get_send_size, 'Sent Data (MiB)', dir)

    get_recv_size = lambda x: x.timing_stats.communication.recv_size if x is not None else 0
    generate_graph_for_attr(all_stats, get_recv_size, 'Received Data (MiB)', dir)  
    generate_cumulative_graph_for_attr(all_stats, get_recv_size, 'Received Data (MiB)', dir)


def get_benchmark_stats(all_stats, benchmark_name, input_label, need_gmw_vec = True):
    for task_stat in all_stats:
        if task_stat.label == benchmark_name:
            for i in range(len(task_stat.input_configs)-1, 0, -1):
                input = task_stat.input_configs[i]
                if input.label == input_label:
                    if need_gmw_vec is True and input.gmw_vec_p0 is not None:
                        return input
                    elif need_gmw_vec is False and input.bmr_vec_p0 is not None:
                        return input 
    return None

def generate_comparison_graphs(lan_stats, wan_stats, get_val, y_label, dir):
    gmwfile = "comparison-gmw-{}.txt".format(y_label)
    bmrfile = "comparison-bmr-{}.txt".format(y_label)
    gmw_hist_graph_file = "comparison-gmw-hist {}{}".format(y_label, GRAPH_EXT)
    bmr_hist_graph_file = "comparison-bmr-hist {}{}".format(y_label, GRAPH_EXT)
    # line_graph_file = "all-line {}{}".format(y_label, GRAPH_EXT)
    gmwfile_path = os.path.join(dir, gmwfile)
    bmrfile_path = os.path.join(dir, bmrfile)
    with open(bmrfile_path, mode='w', encoding='utf-8') as bmrf:
        with open(gmwfile_path, mode='w', encoding='utf-8') as gmwf:
            bmrf.write("x\tBenchmark\t\"LAN\"\t\"WAN\"\tWAN/LAN\tInputLabel\n")
            gmwf.write("x\tBenchmark\t\"LAN\"\t\"WAN\"\tWAN/LAN\tInputLabel\n")
            x = 1
            for lan_task_stat in lan_stats:
                label = get_x_label_for_benchmark(lan_task_stat.label)

                for i in range(len(lan_task_stat.input_configs)-1, 0, -1):
                    lan_input = lan_task_stat.input_configs[i]

                    if lan_input.gmw_vec_p0 is not None:
                        wan_input = get_benchmark_stats(wan_stats, lan_task_stat.label, 
                            lan_input.label, True)
                        if wan_input is not None:
                            lan = get_val(lan_input.gmw_vec_p0)
                            wan  = get_val(wan_input.gmw_vec_p0)
                            r_wan_lan  = ratio(wan, lan)
                            
                            gmwf.write("{x}\t\"{label}\"\t{lan}\t{wan}\t{r_wan_lan}\t\"{input_label}\"\n".format(
                                x=x, label=label, lan=lan, wan=wan, r_wan_lan=r_wan_lan, 
                                input_label=lan_input.label))
                            break

                for i in range(len(lan_task_stat.input_configs)-1, 0, -1):
                    lan_input = lan_task_stat.input_configs[i]

                    if lan_input.bmr_vec_p0 is not None:
                        wan_input = get_benchmark_stats(wan_stats, lan_task_stat.label, 
                            lan_input.label, False)
                        if wan_input is not None:
                            lan = get_val(lan_input.bmr_vec_p0)
                            wan  = get_val(wan_input.bmr_vec_p0)
                            r_wan_lan  = ratio(wan, lan)
                            
                            bmrf.write("{x}\t\"{label}\"\t{lan}\t{wan}\t{r_wan_lan}\t\"{input_label}\"\n".format(
                                x=x, label=label, lan=lan, wan=wan, r_wan_lan=r_wan_lan, 
                                input_label=lan_input.label))
                            break

    gmw_title = "{} - GMW - All Benchmarks".format(y_label)
    bmr_title = "{} - BMR - All Benchmarks".format(y_label)            
    hist_script = os.path.join(FILE_DIR, 'plt_comparison_histogram.gnu')
    # line_script = os.path.join(FILE_DIR, 'plt_linegraph.gnu')
    run_gnuplot(hist_script, gmwfile_path, gmw_hist_graph_file, gmw_title, y_label, dir, other_args = [])
    run_gnuplot(hist_script, bmrfile_path, bmr_hist_graph_file, bmr_title, y_label, dir, other_args = [])
    # run_gnuplot(line_script, file_path, line_graph_file, title, y_label, dir, other_args = [])

def generate_graphs(lan, wan):
    if lan is not True and wan is not True:
        log.error("Need to specify at least one of LAN or WAN directories for source data")
        return

    log.info("LAN dir: {}".format(LAN_DIR))
    log.info("WAN dir: {}".format(WAN_DIR))

    lan_files = [os.path.join(LAN_DIR, f) for f in os.listdir(LAN_DIR) if \
        os.path.isfile(os.path.join(LAN_DIR, f)) and f.endswith('.json')]
    wan_files = [os.path.join(WAN_DIR, f) for f in os.listdir(WAN_DIR) if \
        os.path.isfile(os.path.join(WAN_DIR, f)) and f.endswith('.json')]
    
    lan_stats = []
    for f in lan_files:
        with open(f, "r", encoding='utf-8') as f:
            json_str = f.read()
            file_stats = json_deserialize(json_str)
            lan_stats.append(file_stats)

    wan_stats = []
    for f in wan_files:
        with open(f, "r", encoding='utf-8') as f:
            json_str = f.read()
            file_stats = json_deserialize(json_str)
            wan_stats.append(file_stats)

    if lan is True:
        generate_single_network_graphs(lan_stats, LAN_GRAPHS_DIR)
    if wan is True:
        generate_single_network_graphs(wan_stats, WAN_GRAPHS_DIR)

    if lan is True and wan is True:
        get_num_gates = lambda x: x.circuit_stats.num_gates if x is not None else 0
        generate_comparison_graphs(lan_stats, wan_stats, get_num_gates, 'Total Gates',
            COMPARISON_GRAPHS_DIR)

        get_circ_gen_time = lambda x: x.circuit_stats.circuit_gen_time if x is not None else 0
        generate_comparison_graphs(lan_stats, wan_stats, get_circ_gen_time, 
            'Circuit Generation Time (ms)', COMPARISON_GRAPHS_DIR)

        get_online_time = lambda x: x.timing_stats.gates_online.mean if x is not None else 0
        generate_comparison_graphs(lan_stats, wan_stats, get_online_time, 'Online Time (ms)',
            COMPARISON_GRAPHS_DIR)

        get_setup_time = lambda x: x.timing_stats.gates_setup.mean if x is not None else 0
        generate_comparison_graphs(lan_stats, wan_stats, get_setup_time, 'Setup Time (ms)',
            COMPARISON_GRAPHS_DIR)

        get_send_size = lambda x: x.timing_stats.communication.send_size if x is not None else 0
        generate_comparison_graphs(lan_stats, wan_stats, get_send_size, 'Sent Data (MiB)',
            COMPARISON_GRAPHS_DIR)

        get_recv_size = lambda x: x.timing_stats.communication.recv_size if x is not None else 0
        generate_comparison_graphs(lan_stats, wan_stats, get_recv_size, 'Received Data (MiB)',
            COMPARISON_GRAPHS_DIR)
  

if __name__ == "__main__":
    parser = ArgumentParser(
        description="runs and collects benchmarks statistics for the paper. (assumes correct network config)")
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

    args = parser.parse_args()

    if args.graphs:
        generate_graphs(args.lan, args.wan)
    else:
        run_paper_benchmarks()

