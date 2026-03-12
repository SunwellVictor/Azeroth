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


class _Message:
    def __init__(self, user_id: int = 1, channel_id: int = 2):
        self.author = _Author(user_id)
        self.channel = _Channel(channel_id)
        self.reply = AsyncMock()


class TestEnvFailureHandling(unittest.IsolatedAsyncioTestCase):
    async def test_generation_exception_sends_failure_text(self):
        msg = _Message()
        directives = {"place": "stormwind", "char": "", "creature": "ghoul", "env": True}

        with patch.object(bot_main, "check_guardrails", return_value=False), \
             patch.object(bot_main, "build_messages", return_value=([{"role": "system", "content": "x"}], "")), \
             patch.object(bot_main, "check_cost_control", return_value=(True, "")), \
             patch.object(bot_main, "update_cost_usage", return_value=None), \
             patch.object(bot_main, "generate_rp_response", new=AsyncMock(side_effect=RuntimeError("boom"))):
            await bot_main._handle_env(msg, "Test post.", directives)

        self.assertTrue(msg.reply.await_count >= 1)

    async def test_send_failure_logs_error_event(self):
        msg = _Message()
        directives = {"place": "stormwind", "char": "", "creature": "ghoul", "env": True}

        with patch.object(bot_main, "check_guardrails", return_value=False), \
             patch.object(bot_main, "build_messages", return_value=([{"role": "system", "content": "x"}], "")), \
             patch.object(bot_main, "check_cost_control", return_value=(True, "")), \
             patch.object(bot_main, "update_cost_usage", return_value=None), \
             patch.object(bot_main, "generate_rp_response", new=AsyncMock(return_value="hello")), \
             patch.object(bot_main, "_send_chunks", new=AsyncMock(return_value=False)), \
             patch.object(bot_main, "log_error_event", new=MagicMock()) as log_err:
            await bot_main._handle_env(msg, "Test post.", directives)

        self.assertTrue(log_err.called)


if __name__ == "__main__":
    unittest.main()

