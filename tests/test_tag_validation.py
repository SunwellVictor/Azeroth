import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

from validators import validate_rp_tag_configuration
import main as bot_main


class _Author:
    def __init__(self, user_id: int = 1):
        self.id = user_id
        self.bot = False
        self.guild_permissions = type("P", (), {"manage_messages": False})()


class _Channel:
    def __init__(self, channel_id: int = 2):
        self.id = channel_id


class _Message:
    def __init__(self, content: str):
        self.content = content
        self.author = _Author()
        self.channel = _Channel()
        self.reply = AsyncMock()


class TestTagValidation(unittest.TestCase):
    def test_rejects_multiple_place(self):
        ok, _ = validate_rp_tag_configuration({"env": True, "place": "a", "char": "", "creature": ""}, ["multiple_place"])
        self.assertFalse(ok)

    def test_rejects_char_without_env(self):
        ok, _ = validate_rp_tag_configuration({"env": False, "place": "", "char": "a", "creature": ""}, [])
        self.assertFalse(ok)

    def test_allows_two_char_ids_in_one_tag(self):
        ok, d = validate_rp_tag_configuration({"env": True, "place": "stormwind", "char": "a,b", "creature": ""}, [])
        self.assertTrue(ok)
        self.assertEqual(d["char"], "a")
        self.assertEqual(d["_char_ids"], ["a", "b"])

    def test_rejects_three_char_ids(self):
        ok, _ = validate_rp_tag_configuration({"env": True, "place": "stormwind", "char": "a,b,c", "creature": ""}, [])
        self.assertFalse(ok)

    def test_rejects_comma_creature(self):
        ok, _ = validate_rp_tag_configuration({"env": True, "place": "stormwind", "char": "", "creature": "a,b"}, [])
        self.assertFalse(ok)


class TestTagValidationIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_tag_replies_and_does_not_call_env(self):
        msg = _Message("Test post. !char=a,b,c !env")
        with patch.object(bot_main, "_handle_env", new=AsyncMock()) as h:
            await bot_main.on_message(msg)
        msg.reply.assert_awaited()
        self.assertFalse(h.called)


if __name__ == "__main__":
    unittest.main()

