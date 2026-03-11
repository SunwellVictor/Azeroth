import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

from validators import require_fields

class TestValidators(unittest.TestCase):
    def test_require_fields(self):
        self.assertTrue(require_fields({"id": "x", "name": "y"}, ["id", "name"]))
        self.assertFalse(require_fields({"id": "x"}, ["id", "name"]))

if __name__ == "__main__":
    unittest.main()
