import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

from bindings import load_bindings, resolve_place_id

class TestBindings(unittest.TestCase):
    def test_bindings_empty(self):
        data = load_bindings()
        self.assertIn("channels", data)
        self.assertEqual(resolve_place_id(0), "")

if __name__ == "__main__":
    unittest.main()
