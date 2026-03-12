import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

import main as bot_main


class _Typing:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Channel:
    def __init__(self, channel_id: int):
        self.id = channel_id
        self.send = AsyncMock()

    def typing(self):
        return _Typing()


class _Author:
    def __init__(self, user_id: int):
        self.id = user_id
        self.bot = False
        self.guild_permissions = type("P", (), {"manage_messages": True})()


class _Message:
    def __init__(self, content: str, user_id: int = 1, channel_id: int = 2):
        self.author = _Author(user_id)
        self.channel = _Channel(channel_id)
        self.reply = AsyncMock()
        self.content = content


class TestLoggingEnhancements(unittest.IsolatedAsyncioTestCase):
    async def test_scene_end_logs(self):
        msg = _Message("!scene_end")
        with patch.object(bot_main, "get_state", return_value={"active_place_id": "stormwind"}), \
             patch.object(bot_main, "clear_state", new=MagicMock()), \
             patch.object(bot_main, "log_audit_event_ex", new=MagicMock()) as audit:
            await bot_main.on_message(msg)
        self.assertTrue(audit.called)
        payload = audit.call_args[0][3]
        self.assertIn("place_id", payload)

    async def test_scene_status_logs(self):
        msg = _Message("!scene_status")
        with patch.object(bot_main, "get_state", return_value={"active_place_id": "stormwind", "scene_summary": "", "last_updated": "x"}), \
             patch.object(bot_main, "log_audit_event_ex", new=MagicMock()) as audit:
            await bot_main.on_message(msg)
        self.assertTrue(audit.called)
        payload = audit.call_args[0][3]
        self.assertIn("place_id", payload)
        self.assertIn("summary_present", payload)
        self.assertIn("last_update", payload)

    async def test_env_logs_tags(self):
        msg = _Message("Test !place=stormwind !char=jaina !creature=ghoul !env")
        with patch.object(bot_main, "parse_trailing_directives", return_value=("Test", {"place": "stormwind", "char": "jaina", "creature": "ghoul", "env": True}, [])), \
             patch.object(bot_main, "validate_rp_tag_configuration", return_value=(True, {"place": "stormwind", "char": "jaina", "creature": "ghoul", "env": True})), \
             patch.object(bot_main, "get_state", return_value={"active_place_id": ""}), \
             patch.object(bot_main, "update_state", return_value=None), \
             patch.object(bot_main, "resolve_creature", return_value=({"id": "ghoul"}, "ghoul")), \
             patch.object(bot_main, "build_messages", return_value=([{"role": "system", "content": "x"}], "")), \
             patch.object(bot_main, "check_guardrails", return_value=False), \
             patch.object(bot_main, "check_cost_control", return_value=(True, "")), \
             patch.object(bot_main, "update_cost_usage", return_value=None), \
             patch.object(bot_main, "generate_rp_response", new=AsyncMock(return_value="ok")), \
             patch.object(bot_main, "split_for_discord", return_value=["ok"]), \
             patch.object(bot_main, "_send_chunks", new=AsyncMock(return_value=True)), \
             patch.object(bot_main, "log_audit_event", new=MagicMock()), \
             patch.object(bot_main, "resolve_player_character", return_value="pc1"), \
             patch.object(bot_main, "log_audit_event_ex", new=MagicMock()) as audit_ex:
            await bot_main.on_message(msg)
        self.assertTrue(audit_ex.called)
        calls = audit_ex.call_args_list
        found = False
        for c in calls:
            if c[0][2] == "!env_tags":
                payload = c[0][3]
                self.assertIn("place_id", payload)
                self.assertIn("char_id", payload)
                self.assertIn("creature_id", payload)
                self.assertIn("player_character_id", payload)
                found = True
                break
        self.assertTrue(found)


if __name__ == "__main__":
    unittest.main()

