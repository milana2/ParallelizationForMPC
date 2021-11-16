import unittest

from .context import STAGES_DIR
from .test_stages import StagesTestCase, regenerate_stages


def run_tests():
    unittest.main(module=__name__)
