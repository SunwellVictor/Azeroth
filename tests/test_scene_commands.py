import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

import main as bot_main


class _GuildPermissions:
    def __init__(self, manage_messages: bool):
        self.manage_messages = manage_messages


class _Author:
    def __init__(self, user_id: int, is_bot: bool, manage_messages: bool):
        self.id = user_id
        self.bot = is_bot
        self.guild_permissions = _GuildPermissions(manage_messages)


class _Channel:
    def __init__(self, channel_id: int):
        self.id = channel_id


class _Message:
    def __init__(self, content: str, manage_messages: bool, user_id: int = 1, channel_id: int = 2):
        self.content = content
        self.author = _Author(user_id, False, manage_messages)
        self.channel = _Channel(channel_id)
        self.reply = AsyncMock()


class TestSceneCommands(unittest.IsolatedAsyncioTestCase):
    async def test_scene_end_denied_for_non_mod(self):
        msg = _Message("!scene_end", manage_messages=False)
        with patch.object(bot_main, "clear_state", new=MagicMock()) as clear_state:
            await bot_main.on_message(msg)
        self.assertFalse(clear_state.called)
        msg.reply.assert_awaited()
        self.assertIn("Only moderators may end the active scene.", msg.reply.call_args[0][0])

    async def test_scene_end_clears_for_mod(self):
        msg = _Message("!scene_end", manage_messages=True)
        with patch.object(bot_main, "clear_state", new=MagicMock()) as clear_state, \
             patch.object(bot_main, "log_audit_event_ex", new=MagicMock()) as audit:
            await bot_main.on_message(msg)
        self.assertTrue(clear_state.called)
        self.assertTrue(audit.called)
        msg.reply.assert_awaited()

    async def test_scene_status_replies_with_state(self):
        msg = _Message("!scene_status", manage_messages=False)
        fake_state = {"active_place_id": "stormwind", "scene_summary": "", "last_updated": "2026-01-01T00:00:00Z"}
        with patch.object(bot_main, "get_state", return_value=fake_state), \
             patch.object(bot_main, "log_audit_event_ex", new=MagicMock()) as audit:
            await bot_main.on_message(msg)
        msg.reply.assert_awaited()
        text = msg.reply.call_args[0][0]
        self.assertIn("Scene Status", text)
        self.assertIn("Place: stormwind", text)
        self.assertIn("Summary present: No", text)
        self.assertIn("Last update: 2026-01-01T00:00:00Z", text)
        self.assertTrue(audit.called)


if __name__ == "__main__":
    unittest.main()
