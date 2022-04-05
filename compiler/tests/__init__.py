import sys
import unittest

from .test_stages import StagesTestCase, regenerate_stages
from .paper_benchmarks import run_paper_benchmarks

def run_tests():
    unittest.main(module=__name__, argv=sys.argv[:1])
