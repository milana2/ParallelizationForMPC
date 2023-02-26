#!/usr/bin/env python3

from argparse import ArgumentParser

from tests import run_tests, regenerate_stages
from tests import context as test_context

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate test output to match the current compiler output",
    )
    parser.add_argument(
        "--test-backend",
        choices=["motion"],
        help="Test that the example apps compile and run with the given backend",
    )
    args = parser.parse_args()

    test_context.BACKEND = args.test_backend

    if args.regenerate:
        regenerate_stages()
    else:
        run_tests()
