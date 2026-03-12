import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

from card_loader import DATA_DIR, resolve_player_character


class TestPlayerBindings(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(DATA_DIR, "player_bindings.json")
        self.original = None
        if os.path.isfile(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.original = f.read()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"123": "arhae_drederion"}, f)

    def tearDown(self):
        if self.original is None:
            try:
                os.remove(self.path)
            except Exception:
                pass
        else:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(self.original)

    def test_resolve_player_character(self):
        self.assertEqual(resolve_player_character("123"), "arhae_drederion")
        self.assertIsNone(resolve_player_character("999"))
        self.assertIsNone(resolve_player_character("not_a_number"))


if __name__ == "__main__":
    unittest.main()

