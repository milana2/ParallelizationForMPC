#!/usr/bin/env python3
import argparse

import compiler


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
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    compiler.compile(
        args.input.filename, args.input.read(), args.out_dir, args.overwrite
    )
