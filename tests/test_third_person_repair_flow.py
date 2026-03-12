import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

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


class _Message:
    def __init__(self, user_id: int = 1, channel_id: int = 2):
        self.author = _Author(user_id)
        self.channel = _Channel(channel_id)
        self.reply = AsyncMock()


class TestThirdPersonRepairFlow(unittest.IsolatedAsyncioTestCase):
    async def test_repair_retry_on_second_person(self):
        msg = _Message()
        directives = {"place": "stormwind", "char": "", "creature": "ghoul", "env": True}

        gen = AsyncMock(side_effect=[
            "You hear scraping in the dark.",
            "Lanternlight pools on the cobbles as scraping echoes from the alley."
        ])

        sent = {}

        async def fake_send_chunks(_msg, chunks):
            sent["text"] = chunks[0]
            return True

        with patch.object(bot_main, "check_guardrails", return_value=False), \
             patch.object(bot_main, "build_messages", return_value=([{"role": "system", "content": "x"}], "")), \
             patch.object(bot_main, "check_cost_control", return_value=(True, "")), \
             patch.object(bot_main, "update_cost_usage", return_value=None), \
             patch.object(bot_main, "generate_rp_response", new=gen), \
             patch.object(bot_main, "split_for_discord", side_effect=lambda t, limit=1900: [t]), \
             patch.object(bot_main, "_send_chunks", new=AsyncMock(side_effect=fake_send_chunks)):
            await bot_main._handle_env(msg, "Test post.", directives)

        self.assertIn("Lanternlight pools", sent.get("text", ""))
        self.assertNotIn("You hear", sent.get("text", ""))


if __name__ == "__main__":
    unittest.main()

