"""
========================================================================================
             SAJIM HOLDINGS — TELEGRAM BROADCAST CONNECTION TEST
                   (scripts/test_telegram_connection.py)
========================================================================================
Usage:
  python scripts/test_telegram_connection.py
  python scripts/test_telegram_connection.py --token <TOKEN> --channel <CHANNEL_ID>
========================================================================================
"""

import os
import sys
import argparse
import time

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core")):
    if p not in sys.path:
        sys.path.insert(0, p)

from core.telegram_broadcaster import TelegramBroadcaster


def main():
    parser = argparse.ArgumentParser(description="Test Telegram VIP Broadcast Connection")
    parser.add_argument("--token", type=str, default=None, help="Telegram Bot Token from @BotFather")
    parser.add_argument("--channel", type=str, default=None, help="Telegram Channel username or ID (e.g. @sajim_vip_signals)")
    args = parser.parse_args()

    broadcaster = TelegramBroadcaster()
    if args.token:
        broadcaster.bot_token = args.token
    if args.channel:
        broadcaster.channel_id = args.channel

    if (
        broadcaster.bot_token
        and broadcaster.channel_id
        and "YOUR_BOT_TOKEN" not in broadcaster.bot_token
        and "YOUR_CHANNEL_ID" not in broadcaster.channel_id
    ):
        broadcaster.enabled = True

    print("================================================================================")
    print("           SAJIM HOLDINGS — TELEGRAM VIP BROADCAST HEALTH CHECK                 ")
    print("================================================================================")
    print(f"[*] Bot Token  : {'CONFIGURED' if broadcaster.bot_token and 'YOUR_BOT_TOKEN' not in broadcaster.bot_token else 'MISSING (Set in config/telegram_config.json)'}")
    print(f"[*] Channel ID : {broadcaster.channel_id or 'MISSING (Set in config/telegram_config.json)'}")
    print(f"[*] Status     : {'ARMED & READY' if broadcaster.enabled else 'STANDBY (Needs Token & Channel)'}")
    print("--------------------------------------------------------------------------------")

    if not broadcaster.enabled:
        print("\n[!] To activate Telegram broadcasts:")
        print("    1. Open config/telegram_config.json")
        print("    2. Paste your bot_token from @BotFather")
        print("    3. Paste your channel_id (e.g. @sajim_vip_signals or -1001234567890)")
        print("    4. Ensure the bot is added as an Administrator in your channel with 'Post Messages' permission.")
        return

    test_card = (
        "🏛️ *SAJIM HOLDINGS QUANT LABS — SYSTEM BROADCAST LIVE*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ *Status:* Quant Core & Signal Bus Synchronized\n"
        "💎 *Engine:* Canonical 7-Stage Pipeline (Cheetah + Hummingbird)\n"
        "📊 *Server:* Headway-Real Live Connection Verified\n\n"
        "🎯 *Welcome to Sajim Holdings VIP Institutional Stream!*\n"
        "All verified signals, trade activations, and Break-Even alerts stream here automatically."
    )

    print("[*] Sending test card to Telegram...")
    success = broadcaster._dispatch_http(test_card, parse_mode="Markdown")
    if success:
        print("[+] SUCCESS! Test card delivered to your Telegram channel.")
    else:
        print("[-] FAILED. Check if:")
        print("    - The Bot Token is exact.")
        print("    - The Channel ID is correct.")
        print("    - The bot was added as an ADMIN with 'Post Messages' permission.")


if __name__ == "__main__":
    main()
