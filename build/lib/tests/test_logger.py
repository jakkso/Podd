from os import listdir, path, remove
import unittest

from podd.utilities import logger

TEST_LOG = path.join(path.join(path.dirname(path.dirname(__file__)), 'podd'), 'Logs')


class TestLogger(unittest.TestCase):

    def tearDown(self):
        remove(TEST_LOG + '/test_logger.log')
        pass

    def test_logger(self):
        files = listdir(TEST_LOG)
        test_logger = logger('test_logger')
        # Checks that file isn't created until a log entry is created.
        self.assertNotIn('test_logger.log', files)
        test_logger.info('test message!')
        files = listdir(TEST_LOG)
        self.assertIn('test_logger.log', files)
        with open(TEST_LOG + '/test_logger.log', 'r') as file:
            line = file.read()
        self.assertIn('test message!', line)


if __name__ == '__main__':
    unittest.main()
