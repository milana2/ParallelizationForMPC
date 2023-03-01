#!/usr/bin/env python3
import argparse

import compiler
from compiler.backends import Backend


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=argparse.FileType("r"))
    parser.add_argument(
        "--out-dir",
        help="If provided, render a sample application into this directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output directory",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Avoid printing output of compiler stages",
    )
    parser.add_argument(
        "--protocol",
        help="Protocol to use when running benchmarks",
    )
    parser.add_argument(
        "--backend",
        type=Backend,
        choices=list(Backend),
        help="The MPC backend to target",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    compiler.compile(
        args.input.name,
        args.input.read(),
        args.backend,
        args.quiet,
        True,  # Only output vectorized code when invoked from the command line
        args.out_dir,
        args.overwrite,
        args.protocol,
    )
