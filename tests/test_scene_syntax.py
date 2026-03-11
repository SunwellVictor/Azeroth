import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

from scene_syntax import parse_trailing_directives

class TestSceneSyntax(unittest.TestCase):
    def test_place_env(self):
        rp, d, w = parse_trailing_directives("Hello there !place=silvermoon !env")
        self.assertEqual(rp, "Hello there")
        self.assertEqual(d["place"], "silvermoon")
        self.assertTrue(d["env"])
        self.assertEqual(w, [])

    def test_env_only(self):
        rp, d, w = parse_trailing_directives("She waits. !env")
        self.assertEqual(rp, "She waits.")
        self.assertTrue(d["env"])

    def test_ignores_middle_directives(self):
        rp, d, w = parse_trailing_directives("He says !place=silvermoon in prose and continues !env")
        self.assertEqual(d["place"], "")
        self.assertTrue(d["env"])

    def test_last_wins(self):
        rp, d, w = parse_trailing_directives("X !place=stormwind !place=silvermoon !env")
        self.assertEqual(d["place"], "silvermoon")
        self.assertIn("multiple_place", w)

    def test_normalizes_case(self):
        rp, d, w = parse_trailing_directives("X !char=SYLVANAS !env")
        self.assertEqual(d["char"], "sylvanas")

if __name__ == "__main__":
    unittest.main()

