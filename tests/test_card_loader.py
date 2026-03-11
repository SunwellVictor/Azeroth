import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

from card_loader import load_characters, load_places, load_creatures

class TestCardLoader(unittest.TestCase):
    def test_loaders(self):
        chars = load_characters()
        places = load_places()
        creatures = load_creatures()
        self.assertIsInstance(chars, list)
        self.assertIsInstance(places, list)
        self.assertIsInstance(creatures, list)

    def test_seed_ids_present(self):
        place_ids = {p.get("id") for p in load_places()}
        char_ids = {c.get("id") for c in load_characters()}
        creature_ids = {c.get("id") for c in load_creatures()}

        self.assertIn("silvermoon", place_ids)
        self.assertIn("stormwind", place_ids)
        self.assertIn("orgrimmar", place_ids)

        self.assertIn("sylvanas", char_ids)
        self.assertIn("jaina", char_ids)
        self.assertIn("thrall", char_ids)
        # Optional originals may vary; assert core canon seeds

        self.assertIn("worg", creature_ids)
        self.assertIn("ghoul", creature_ids)

if __name__ == "__main__":
    unittest.main()
