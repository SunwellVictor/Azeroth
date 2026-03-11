import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

from scene_memory import clear_state, update_state
from response_engine import build_messages

class TestResponseEngine(unittest.TestCase):
    def setUp(self):
        clear_state(777)

    def test_place_only_prompt(self):
        update_state(777, place_id="silvermoon")
        msgs, err = build_messages(777, "Test post.", "silvermoon")
        self.assertEqual(err, "")
        self.assertIsInstance(msgs, list)

    def test_place_char_prompt(self):
        update_state(777, place_id="stormwind")
        msgs, err = build_messages(777, "Test post.", "stormwind", char_id="jaina")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertIn("ACTIVE CHARACTER CARD", sys_content)

    def test_place_creature_prompt(self):
        update_state(777, place_id="orgrimmar")
        msgs, err = build_messages(777, "Test post.", "orgrimmar", creature_id="worg")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertIn("ACTIVE CREATURE CARD", sys_content)

    def test_creature_resolves_by_alias(self):
        update_state(777, place_id="stormwind")
        msgs, err = build_messages(777, "Test post.", "stormwind", creature_id="scourge_ghoul")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertIn("ACTIVE CREATURE CARD", sys_content)
        self.assertIn("ID: ghoul", sys_content)

    def test_creature_tag_overrides_place_monster_table(self):
        update_state(777, place_id="stormwind")
        msgs, err = build_messages(777, "Test post.", "stormwind", creature_id="ghoul")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertIn("ACTIVE CREATURE CARD", sys_content)

    def test_creature_tag_works_cross_location(self):
        update_state(777, place_id="orgrimmar")
        msgs, err = build_messages(777, "Test post.", "orgrimmar", creature_id="ghoul")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertIn("ACTIVE CREATURE CARD", sys_content)

    def test_creature_resolves_dust_wolf_in_silvermoon(self):
        update_state(777, place_id="silvermoon")
        msgs, err = build_messages(777, "Test post.", "silvermoon", creature_id="dust_wolf")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertIn("ACTIVE CREATURE CARD", sys_content)
        self.assertIn("ID: wolf", sys_content)

    def test_place_char_creature_prompt(self):
        update_state(777, place_id="stormwind")
        msgs, err = build_messages(777, "Test post.", "stormwind", char_id="jaina", creature_id="ghoul")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertIn("ACTIVE CHARACTER CARD", sys_content)
        self.assertIn("ACTIVE CREATURE CARD", sys_content)

    def test_invalid_place(self):
        msgs, err = build_messages(777, "Test post.", "missing_place")
        self.assertIsNone(msgs)
        self.assertNotEqual(err, "")

    def test_invalid_char(self):
        msgs, err = build_messages(777, "Test post.", "stormwind", char_id="missing_char")
        self.assertIsNone(msgs)
        self.assertIn("Unknown character id", err)

    def test_invalid_creature(self):
        msgs, err = build_messages(777, "Test post.", "stormwind", creature_id="missing_creature")
        self.assertIsNone(msgs)
        self.assertIn("Unknown creature id", err)
        self.assertIn("available:", err)

if __name__ == "__main__":
    unittest.main()
