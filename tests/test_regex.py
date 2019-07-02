"""Test compiled regex."""
import unittest as ut

from podd.utilities import compile_regex, get_episode_number

PATTERNS = compile_regex()


class TestCompiledRegex(ut.TestCase):
    """Test compiled regex patterns.

    There are five patterns, each testing for a different pattern.
    """

    def test_pattern_one(self):
        """Test first pattern.

        This pattern is supposed to capture episode numbers that follow
        the pattern `EPISODE #?(\d+)`
        """
        pat = PATTERNS[0]
        s = "EPISODE 44 Dan Carlin"
        res = pat.search(s)
        self.assertIsNotNone(res)
        self.assertEqual('44', res.groups()[0])
        s2 = s.lower()
        res = pat.search(s2)
        self.assertIsNotNone(res)
        self.assertEqual('44', res.groups()[0])

    def test_get_episode_number(self) -> None:
        """Test stand-alone `get_episode_number` function.

        `get_episode_number` is a functional equivilent to the Episode bound method.
        This makes it easier to test.
        """
        with open('testfiles/ep-nums.txt') as file:
            good_strs = [i for i in file]
        for s in good_strs:
            num = get_episode_number(s)
            self.assertIsNone(num)
        with open('testfiles/no-ep-num.txt') as file:
            bad_strs = [i for i in file]
        for s in bad_strs:
            num = get_episode_number(s)
            self.assertIsNone(num)


if __name__ == '__main__':
    ut.main()
