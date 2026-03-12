import os
import sys
import unittest
from unittest.mock import mock_open, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "azerbot"))

from utils import log_debug_event


class TestDebugLogging(unittest.TestCase):
    def test_log_debug_event_writes_jsonl(self):
        m = mock_open()
        with patch("builtins.open", m):
            log_debug_event({"event_type": "env_debug", "x": 1})
        m.assert_called()
        handle = m()
        handle.write.assert_called()


if __name__ == "__main__":
    unittest.main()

