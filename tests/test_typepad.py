import os
import unittest

import nose

import typepad
from tests import utils


class TestTypePad(unittest.TestCase):

    def setUp(self):
        if not os.getenv('TEST_TYPEPAD'):
            raise nose.SkipTest('no typepad tests without TEST_TYPEPAD=1')
        super(TestTypePad, self).setUp()

    @utils.todo
    def test_typepad(self):
        raise NotImplementedError()
