#!/usr/bin/env python3

from argparse import ArgumentParser

from tests import run_tests, regenerate_stages

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate test output to match the current compiler output",
    )
    args = parser.parse_args()

    if args.regenerate:
        regenerate_stages()
    else:
        run_tests()
