import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

from scene_memory import clear_state, get_state, update_state

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

    def test_place_change_resets_creature(self):
        update_state(123, place_id="stormwind", creature_id="wolf")
        update_state(123, place_id="silvermoon", place_changed=True)
        st = get_state(123)
        self.assertEqual(st["active_place_id"], "silvermoon")
        self.assertEqual(st["active_creature_id"], "")

    def test_place_change_preserves_creature_if_explicit(self):
        update_state(123, place_id="stormwind", creature_id="wolf")
        update_state(123, place_id="silvermoon", creature_id="worg", place_changed=True)
        st = get_state(123)
        self.assertEqual(st["active_creature_id"], "worg")

if __name__ == "__main__":
    unittest.main()
