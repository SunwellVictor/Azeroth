import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

from utils import is_strict_third_person, third_person_violations


class TestThirdPersonValidator(unittest.TestCase):
    def test_allows_third_person(self):
        text = "The lanternlight pools on the cobbles as the wind threads the alley."
        self.assertTrue(is_strict_third_person(text))

    def test_blocks_second_person_outside_quotes(self):
        text = "You hear scraping in the dark."
        self.assertFalse(is_strict_third_person(text))
        self.assertIn("you", third_person_violations(text))

    def test_ignores_second_person_inside_quotes(self):
        text = "The guard raises a hand. \"You there—halt.\" The patrol does not slow."
        self.assertTrue(is_strict_third_person(text))

    def test_blocks_first_person_outside_quotes(self):
        text = "I step into the street and listen."
        self.assertFalse(is_strict_third_person(text))


if __name__ == "__main__":
    unittest.main()

