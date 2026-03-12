import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

from scene_memory import clear_state, get_state, update_state, MAX_SUMMARY_LENGTH

class TestSceneMemory(unittest.TestCase):
    def setUp(self):
        clear_state(123)

    def test_place_persists(self):
        update_state(123, place_id="silvermoon")
        st = get_state(123)
        self.assertEqual(st["active_place_id"], "silvermoon")

    def test_env_without_place_reuses(self):
        update_state(123, place_id="stormwind")
        st = get_state(123)
        self.assertEqual(st["active_place_id"], "stormwind")

    def test_char_and_creature_do_not_persist(self):
        update_state(123, place_id="stormwind", char_id="sylvanas", creature_id="wolf")
        st = get_state(123)
        self.assertEqual(st["active_place_id"], "stormwind")
        self.assertEqual(st["active_char_id"], "")
        self.assertEqual(st["active_creature_id"], "")

        update_state(123, scene_summary="test")
        st = get_state(123)
        self.assertEqual(st["scene_summary"], "test")

        update_state(123, place_id="silvermoon", place_changed=True)
        st = get_state(123)
        self.assertEqual(st["active_place_id"], "silvermoon")
        self.assertEqual(st["scene_summary"], "")

    def test_scene_summary_capped(self):
        long_summary = ("word " * 100).strip()
        update_state(123, scene_summary=long_summary)
        st = get_state(123)
        self.assertLessEqual(len(st["scene_summary"]), MAX_SUMMARY_LENGTH)
        self.assertFalse(st["scene_summary"].endswith(" "))

if __name__ == "__main__":
    unittest.main()
