
import os
import sys
import subprocess

import logging # To support logging
import logging.handlers # To enable multiple handlers with logging (e.g. a rotating file handler)
import random

import compiler

from . import context as test_context
from .benchmark import run_benchmark

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


random.seed(0) # Intentionally seeding with a known value, for reproducibility
def get_rand_ints(n):
    return [random.randint(1, 100) for i in range(n)]


def run_paper_benchmarks():

    for protocol in compiler.motion_backend.VALID_PROTOCOLS:
            for test_case_dir in os.scandir(test_context.STAGES_DIR):
                # if test_case_dir.name in test_context.SKIPPED_TESTS:
                #     continue
                if test_case_dir.name != "biometric":
                    continue;

                input_fname = os.path.join(test_case_dir.path, "input.py")

                cmd_args = [
                    "--D", "4",
                    "--N", "4"
                    ]
                C = get_rand_ints(4)
                S = get_rand_ints(16)
                cmd_args.append("--C")
                cmd_args.extend(list(map(str, C)))
                cmd_args.append("--S")
                cmd_args.extend(list(map(str, S)))

                log.debug("args: {}".format(cmd_args))
                log.debug("Running {} {} {}\n".format(test_case_dir.name, test_case_dir.path, protocol));
                party0, party1 = run_benchmark(
                    test_case_dir.name, test_case_dir.path, protocol,
                    True, cmd_args, False
                )

                log.info("output is {}".format(party0.output.strip()))

                assert party0.output.strip() == party1.output.strip(), (party0.output.strip(), party1.output.strip())

