import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

from scene_memory import clear_state, update_state
from response_engine import build_messages
from card_loader import DATA_DIR

class TestResponseEngine(unittest.TestCase):
    def setUp(self):
        clear_state(777)

    def test_place_only_prompt(self):
        update_state(777, place_id="silvermoon")
        msgs, err = build_messages(777, "Test post.", "silvermoon")
        self.assertEqual(err, "")
        self.assertIsInstance(msgs, list)
        sys_content = msgs[0]["content"]
        self.assertIn("Prefer 1–2 compact paragraphs", sys_content)
        self.assertIn("Target roughly 400–900 characters", sys_content)
        self.assertIn("Never control the player's character", sys_content)
        self.assertIn("PLAYER CHARACTER SAFETY RULES:", sys_content)

    def test_player_character_card_injected_when_bound(self):
        bindings_path = os.path.join(DATA_DIR, "player_bindings.json")
        pc_dir = os.path.join(DATA_DIR, "player_characters")
        os.makedirs(pc_dir, exist_ok=True)
        pc_id = "unit_test_pc_bound"
        pc_path = os.path.join(pc_dir, f"{pc_id}.txt")

        original = None
        if os.path.isfile(bindings_path):
            with open(bindings_path, "r", encoding="utf-8") as f:
                original = f.read()
        with open(bindings_path, "w", encoding="utf-8") as f:
            f.write('{"1": "' + pc_id + '"}')
        with open(pc_path, "w", encoding="utf-8") as f:
            f.write("UNIT TEST PC\nSome details.\n")

        try:
            update_state(777, place_id="stormwind", scene_summary="")
            msgs, err = build_messages(777, "Test post.", "stormwind", user_id="1")
            self.assertEqual(err, "")
            sys_content = msgs[0]["content"]
            self.assertIn("PLAYER CHARACTER CARD (automatic context):", sys_content)
            self.assertIn("ID: " + pc_id, sys_content)
            self.assertIn("UNIT TEST PC", sys_content)
        finally:
            try:
                os.remove(pc_path)
            except Exception:
                pass
            if original is None:
                try:
                    os.remove(bindings_path)
                except Exception:
                    pass
            else:
                with open(bindings_path, "w", encoding="utf-8") as f:
                    f.write(original)

    def test_place_char_prompt(self):
        update_state(777, place_id="stormwind")
        msgs, err = build_messages(777, "Test post.", "stormwind", char_id="jaina")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertIn("ACTIVE CHARACTER CARD", sys_content)
        self.assertIn("CHARACTER PRESENCE POLICY", sys_content)

    def test_char_conservative_when_not_addressed(self):
        update_state(777, place_id="silvermoon", scene_summary="")
        post = "Lanternlight holds steady over white stone."
        msgs, err = build_messages(777, post, "silvermoon", char_id="sylvanas")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertIn("CHARACTER_INTERACTION_PERMISSION: conservative_presence", sys_content)

    def test_char_direct_response_allowed_when_addressed(self):
        update_state(777, place_id="silvermoon", scene_summary="")
        post = "Sylvanas, speak."
        msgs, err = build_messages(777, post, "silvermoon", char_id="sylvanas")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertIn("CHARACTER_INTERACTION_PERMISSION: direct_address_allowed", sys_content)

    def test_char_does_not_persist_between_calls(self):
        update_state(777, place_id="silvermoon")
        msgs, err = build_messages(777, "Test post.", "silvermoon", char_id="sylvanas")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertIn("ACTIVE CHARACTER CARD", sys_content)

        update_state(777, place_id="orgrimmar")
        msgs, err = build_messages(777, "Test post.", "orgrimmar", creature_id="dust_wolf")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertNotIn("ACTIVE CHARACTER CARD", sys_content)
        self.assertIn("ACTIVE CREATURE CARD", sys_content)

    def test_scene_summary_not_used_for_char_continuity(self):
        update_state(777, place_id="silvermoon", scene_summary="Sylvanas whispers: I own this place.")
        update_state(777, place_id="orgrimmar", place_changed=True)
        msgs, err = build_messages(777, "Test post.", "orgrimmar", creature_id="dust_wolf")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertNotIn("Sylvanas whispers", sys_content)

    def test_place_creature_prompt(self):
        update_state(777, place_id="orgrimmar")
        msgs, err = build_messages(777, "Test post.", "orgrimmar", creature_id="worg")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertIn("ACTIVE CREATURE CARD", sys_content)

    def test_creature_escalation_pressure_default(self):
        update_state(777, place_id="stormwind", scene_summary="")
        post = "The alley stinks of rot, and something scrapes against the stone."
        msgs, err = build_messages(777, post, "stormwind", creature_id="ghoul")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertIn("ESCALATION_PERMISSION: pressure_only", sys_content)

    def test_creature_escalation_allows_direct_when_cued(self):
        update_state(777, place_id="stormwind", scene_summary="")
        post = "The ghoul lunges from the alley mouth."
        msgs, err = build_messages(777, post, "stormwind", creature_id="ghoul")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertIn("ESCALATION_PERMISSION: direct_confrontation_allowed", sys_content)

    def test_creature_escalation_cross_place_pressure(self):
        update_state(777, place_id="orgrimmar", scene_summary="")
        post = "Dust curls over the road beyond the gates. Something is out there."
        msgs, err = build_messages(777, post, "orgrimmar", creature_id="dust_wolf")
        self.assertEqual(err, "")
        sys_content = msgs[0]["content"]
        self.assertIn("ESCALATION_PERMISSION: pressure_only", sys_content)
        self.assertNotIn("ACTIVE CHARACTER CARD", sys_content)

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
