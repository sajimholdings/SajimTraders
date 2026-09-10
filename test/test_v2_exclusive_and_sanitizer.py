import unittest
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.telegram_broadcaster import TelegramBroadcaster
from core.beep_broadcast import clean_html_text, ALLOW_V1_BROADCASTS, BeepBroadcastBus

class TestV2ExclusiveAndSanitizer(unittest.TestCase):

    def test_clean_html_text(self):
        raw = "Young Bullish Surge: Maturity=0.53 <= 0.60 | TrendCount=10/19.0 bars | Close > HMA-50 & Score >= 48"
        cleaned = clean_html_text(raw)
        self.assertNotIn("<=", cleaned)
        self.assertIn("&lt;=", cleaned)
        self.assertIn("&amp;", cleaned)
        self.assertIn("&gt;", cleaned)

    def test_sanitize_telegram_html(self):
        # Text with valid tags AND illegal raw angle brackets
        raw_msg = (
            "<b>[SAJIM V2] TREND DURATION SIGNAL: NASDAQ-100 (M15)</b>\n"
            "• Maturity: 0.53 <= 0.60\n"
            "• Score < 48.0\n"
            "• Close > HMA-50\n"
            "<i>Valid italics with & symbol</i>\n"
            "<code>Valid code block</code>"
        )
        sanitized = TelegramBroadcaster.sanitize_telegram_html(raw_msg)
        self.assertIn("<b>[SAJIM V2]", sanitized)
        self.assertIn("</b>", sanitized)
        self.assertIn("<i>Valid italics", sanitized)
        self.assertIn("<code>Valid code", sanitized)
        self.assertNotIn("<= 0.60", sanitized)
        self.assertIn("&lt;= 0.60", sanitized)
        self.assertNotIn("< 48.0", sanitized)
        self.assertIn("&lt; 48.0", sanitized)

    def test_v1_broadcast_suppression(self):
        self.assertFalse(ALLOW_V1_BROADCASTS)
        bus = BeepBroadcastBus()
        # V1 signal event should NOT send to telegram
        v1_event = bus.broadcast_signal(
            symbol="EURUSD",
            timeframe="M15",
            action="BUY",
            layer="DIAMOND",
            m_t=85.0,
            entry=1.0850,
            sl=1.0820,
            tp=1.0910,
            rr=2.0
        )
        self.assertEqual(v1_event["type"], "SIGNAL_GENERATED")
        print("v1_broadcast_suppression test passed")

if __name__ == "__main__":
    unittest.main()
