
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
def get_rand_ints(n):
    return [random.randint(1, 100) for i in range(n)]

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

def get_psi_inputs()-> tuple[list[InputArgs], int]:
    all_args = []
    non_vec_up_to = 6
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
def get_cryptonets_convolution_naive_inputs():
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

def get_inputs(name: str) -> tuple[list[InputArgs], int]:
    if name == "biometric" or name == "biometric_fast":
         return get_biometric_inputs()
    if name == "psi":
        return get_psi_inputs()
    if name == "inner_product":
        return get_inner_product_inputs()
    if name == "convex_hull":
        return get_convex_hull_inputs()
    if name == "cryptonets_convolution_naive":
        return get_cryptonets_convolution_naive_inputs()
    return [[], 0]


def print_protocol_stats(p0, vec_p0, p1, vec_p1,):
    ts0 = cs0 = None
    if p0 is not None:
        ts0 = p0.timing_stats
        cs0 = p0.circuit_stats
        
    ts1 = None
    if p1 is not None:
        ts1 = p1.timing_stats

    ts0v = vec_p0.timing_stats
    cs0v = vec_p0.circuit_stats
    ts1v = vec_p1.timing_stats



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

def print_benchmark_data(filename):
    with open(filename, "r", encoding='utf-8') as f:
        json_str = f.read()
        all_stats = json_deserialize(json_str)

    log.info("Listing All Benchmark Stats")
    for task_stats in all_stats:
        log.info("="*80)
        
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


def run_paper_benchmarks(filename):
    all_stats = []
    for test_case_dir in os.scandir(test_context.STAGES_DIR):
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
                    log.info("GMW Non Vectorized FAILED! Will not run Non-Vectorized from now.")
                    non_vec_failed = True
            
            log.info("Running GMW Vectorized {} {}".format(test_case_dir.name, args.label));
            gmw_vec_p0, gmw_vec_p1 = run_benchmark(
                test_case_dir.name, test_case_dir.path, GMW_PROTOCOL, True, None, args.args, compile
            )
            log.info("GMW Vectorized output is {}".format(gmw_vec_p0.output.strip()))
            assert gmw_vec_p0.output.strip() == gmw_vec_p1.output.strip(), \
                (gmw_vec_p0.output.strip(), gmw_vec_p1.output.strip())

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
                    log.info("BMR Non Vectorized FAILED! Will not run Non-Vectorized from now.")
                    non_vec_failed = True
            
            log.info("Running BMR Vectorized {} {}".format(test_case_dir.name, args.label));
            bmr_vec_p0, bmr_vec_p1 = run_benchmark(
                test_case_dir.name, test_case_dir.path, BMR_PROTOCOL, True, None, args.args, compile
            )
            log.info("BMR Vectorized output is {}".format(bmr_vec_p0.output.strip()))
            assert bmr_vec_p0.output.strip() == bmr_vec_p1.output.strip(), \
                (bmr_vec_p0.output.strip(), bmr_vec_p1.output.strip())
            
            compile = False

            
            input_stats = StatsForInputConfig(args.label, gmw_p0, gmw_p1, gmw_vec_p0, gmw_vec_p1,
                bmr_p0, bmr_p1, bmr_vec_p0, bmr_vec_p1)
            task_stats.input_configs.append(input_stats)
            log.info("task {} input config {} DONE".format(task_stats.label, input_stats.label))

            with open("{}.json".format(task_stats.label), "w", encoding='utf-8') as f:
                json_str = json_serialize(all_stats)
                f.write(json_str)
            
            i += 1

        all_stats.append(task_stats)
        log.info("task {} DONE".format(task_stats.label))
        with open(filename, "w", encoding='utf-8') as f:
            json_str = json_serialize(all_stats)
            f.write(json_str)

    print_benchmark_data(filename)
    generate_graphs([filename])


def run_gnuplot(plot_script, data_file, graph_file, title, y_label, other_args = []):
    log.info("gnuplot -c {} {} {} \"{}\" \"{}\" {}".format(plot_script, 
        data_file, graph_file, title, y_label, other_args)
    )
    with subprocess.Popen(
        [
            "gnuplot",
            "-c", plot_script,
            data_file, graph_file,
            "\"{}\"".format(title), "\"{}\"".format(y_label)
        ] + other_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=GRAPHS_DIR
    ) as gnuplot:
        gnuplot.wait()
        if(gnuplot.returncode != 0):
            log.error("gnuplot exited with returncode: {0}".format(gnuplot.returncode))
            log.error("stderr: \n{0}".format(gnuplot.stderr.read()))
            log.debug("stdout: \n{0}".format(gnuplot.stdout.read()))
            exit(1)

    # gnuplot -c histogram.gnu data_file.txt graph.png "Graph Title" "Y Axis Label"
    # gnuplot -c linegraph.gnu data_file.txt graph.png "Graph Title" "Y Axis Label"
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

    pass

def generate_graphs(source_files):
    all_stats = []
    for sf in source_files:
        with open(sf, "r", encoding='utf-8') as f:
            json_str = f.read()
            file_stats = json_deserialize(json_str)
            all_stats.extend(file_stats)

    FILE_DIR = os.path.dirname(__file__)
    GRAPHS_DIR = os.path.join(FILE_DIR, "graphs")
    os.makedirs(GRAPHS_DIR, exist_ok=True)

    # Total Gates
    for task_stat in all_stats:
        fname = "{}-total-gates.txt".format(task_stat.label)
        file_path = os.path.join(GRAPHS_DIR, fname)
        with open(file_path, mode='w', encoding='utf-8') as f:
            f.write("x\tInput\tNonVec(GMW)\tVec(GMW)\tNonVec(BMR)\tVec(BMR)\tRatio(GMW)\tRatio(BMR)\n")
            x = 1
            for i in task_stat.input_configs:
                label = i.label

                nv_gmw = i.gmw_p0.circuit_stats.num_gates if i.gmw_p0 is not None else 0
                v_gmw  = i.gmw_vec_p0.circuit_stats.num_gates
                r_gmw  = nv_gmw/v_gmw

                nv_bmr = i.bmr_p0.circuit_stats.num_gates if i.bmr_p0 is not None else 0
                v_bmr  = i.bmr_vec_p0.circuit_stats.num_gates
                r_bmr  = nv_bmr/v_bmr

                f.write("{x}\t\"{label}\"\t{nv_gmw}\t{v_gmw}\t{nv_bmr}\t{v_bmr}\t{r_gmw}\t{r_bmr}\n".format(
                    x=x, label=label, nv_gmw=nv_gmw, v_gmw=v_gmw, r_gmw=r_gmw, nv_bmr=nv_bmr, v_bmr=v_bmr, 
                    r_bmr=r_bmr))
                x += 1

    # Circ Gen Time
    for task_stat in all_stats:
        fname = "{}-circ-gen.txt".format(task_stat.label)
        file_path = os.path.join(GRAPHS_DIR, fname)
        with open(file_path, mode='w', encoding='utf-8') as f:
            f.write("x\tInput\tNonVec(GMW)\tVec(GMW)\tNonVec(BMR)\tVec(BMR)\tRatio(GMW)\tRatio(BMR)\n")
            x = 1
            for i in task_stat.input_configs:
                label = i.label

                nv_gmw = i.gmw_p0.circuit_stats.circuit_gen_time if i.gmw_p0 is not None else 0
                v_gmw  = i.gmw_vec_p0.circuit_stats.circuit_gen_time
                r_gmw  = nv_gmw/v_gmw

                nv_bmr = i.bmr_p0.circuit_stats.circuit_gen_time if i.bmr_p0 is not None else 0
                v_bmr  = i.bmr_vec_p0.circuit_stats.circuit_gen_time
                r_bmr  = nv_bmr/v_bmr

                f.write("{x}\t\"{label}\"\t{nv_gmw}\t{v_gmw}\t{nv_bmr}\t{v_bmr}\t{r_gmw}\t{r_bmr}\n".format(
                    x=x, label=label, nv_gmw=nv_gmw, v_gmw=v_gmw, r_gmw=r_gmw, nv_bmr=nv_bmr, v_bmr=v_bmr, 
                    r_bmr=r_bmr))
                x += 1
    
    # gnuplot -c histogram.gnu data_file.txt graph.png "Graph Title" "Y Axis Label"
    # gnuplot -c linegraph.gnu data_file.txt graph.png "Graph Title" "Y Axis Label"
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
    parser.add_argument('-f', '--files', nargs='+', 
        help="files load/store benchmark data, only the first is used when storing", 
        default=["benchmarks.json"],
    )

    args = parser.parse_args()

    if args.graphs:
        generate_graphs(args.files)
    else:
        run_paper_benchmarks(args.files[0])

