from os import listdir, remove
import pathlib
import unittest

from podd.utilities import logger

TEST_LOG = pathlib.Path(__file__).parent.parent / 'podd' / 'Logs'


class TestLogger(unittest.TestCase):

    def tearDown(self):
        remove(TEST_LOG / 'test_logger.log')

    def test_logger(self):
        print(TEST_LOG)
        files = listdir(TEST_LOG)
        test_logger = logger('test_logger', TEST_LOG)
        # Checks that file isn't created until a log entry is created.
        self.assertNotIn('test_logger.log', files)
        test_logger.info('test message!')
        files = listdir(TEST_LOG)
        self.assertIn('test_logger.log', files)
        with open(TEST_LOG / 'test_logger.log', 'r') as file:
            line = file.read()
        self.assertIn('test message!', line)


if __name__ == '__main__':
    unittest.main()
