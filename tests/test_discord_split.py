import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

from utils import split_for_discord


class TestDiscordSplit(unittest.TestCase):
    def test_short_sends_once(self):
        parts = split_for_discord("Hello world.", 1900)
        self.assertEqual(parts, ["Hello world."])

    def test_long_splits_two_or_more(self):
        text = ("A" * 1000) + "\n\n" + ("B" * 1000) + "\n\n" + ("C" * 1000)
        parts = split_for_discord(text, 1900)
        self.assertGreaterEqual(len(parts), 2)
        for p in parts:
            self.assertLessEqual(len(p), 1900)

    def test_prefers_sentence_boundary(self):
        sentence = "This is a sentence."
        text = (" ".join([sentence] * 200)).strip()
        parts = split_for_discord(text, 1900)
        self.assertGreaterEqual(len(parts), 2)
        self.assertTrue(parts[0].endswith(".") or parts[0].endswith("!") or parts[0].endswith("?"))
        for p in parts:
            self.assertLessEqual(len(p), 1900)

    def test_never_cuts_mid_word(self):
        text = ("word " * 800).strip()
        parts = split_for_discord(text, 1900)
        original_tokens = text.split()
        rejoined_tokens = (" ".join(parts)).split()
        self.assertEqual(original_tokens, rejoined_tokens)


if __name__ == "__main__":
    unittest.main()
