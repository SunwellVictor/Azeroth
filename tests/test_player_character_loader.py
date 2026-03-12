import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

from card_loader import load_player_character, DATA_DIR


class TestPlayerCharacterLoader(unittest.TestCase):
    def setUp(self):
        self.dir_path = os.path.join(DATA_DIR, "player_characters")
        os.makedirs(self.dir_path, exist_ok=True)
        self.card_id = "unit_test_pc"
        self.file_path = os.path.join(self.dir_path, f"{self.card_id}.txt")
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("UNIT TEST PC\nLine two.\n")

    def tearDown(self):
        try:
            os.remove(self.file_path)
        except Exception:
            pass

    def test_load_player_character_reads_text(self):
        text = load_player_character(self.card_id)
        self.assertIsInstance(text, str)
        self.assertIn("UNIT TEST PC", text)

    def test_load_player_character_missing_returns_none(self):
        self.assertIsNone(load_player_character("missing_card_123"))


if __name__ == "__main__":
    unittest.main()

