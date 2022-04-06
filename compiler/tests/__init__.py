import sys
import unittest

from .test_stages import StagesTestCase, regenerate_stages

def run_tests():
    unittest.main(module=__name__, argv=sys.argv[:1])
