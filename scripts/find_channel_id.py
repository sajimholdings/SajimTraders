"""
========================================================================================
             SAJIM HOLDINGS — TELEGRAM CHANNEL ID AUTO-DISCOVERY TOOL
========================================================================================
Chief Architect: Jimmy Mathu

Usage:
  1. Add @sajim_quant_bot as an ADMINISTRATOR to your Telegram Channel.
  2. Send any test message in the channel (e.g. "Sajim Live Test").
  3. Run this script:
     python scripts/find_channel_id.py
========================================================================================
"""

import os
import sys
import json
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
CONFIG_FILE = os.path.join(ROOT_DIR, "config", "telegram_config.json")

def main():
    if not os.path.exists(CONFIG_FILE):
        print(f"[!] Config file not found at {CONFIG_FILE}")
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    token = cfg.get("bot_token")
    if not token or "BOTFATHER" in token:
        print("[!] Please configure bot_token in config/telegram_config.json first.")
        return

    print(f"[*] Querying updates for bot token: {token[:10]}...{token[-5:]}")
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[!] Error contacting Telegram API: {e}")
        return

    if not data.get("ok"):
        print(f"[!] API Error: {data}")
        return

    results = data.get("result", [])
    if not results:
        print("\n[?] No recent updates found!")
        print("--> Have you added @sajim_quant_bot as an ADMIN to your channel?")
        print("--> Have you posted at least ONE message in your channel after adding the bot?")
        print("    Please post a message in the channel right now, then re-run this script.\n")
        return

    channels_found = []
    for update in results:
        # Check channel_post or message
        chat = None
        if "channel_post" in update:
            chat = update["channel_post"].get("chat")
        elif "message" in update:
            chat = update["message"].get("chat")
        elif "my_chat_member" in update:
            chat = update["my_chat_member"].get("chat")

        if chat:
            chat_id = chat.get("id")
            title = chat.get("title", chat.get("username", "Private/Unknown"))
            chat_type = chat.get("type", "unknown")
            channels_found.append((chat_id, title, chat_type))

    if not channels_found:
        print("[!] No channels or groups detected in updates.")
        return

    print(f"\n[+] Detected {len(channels_found)} active chat(s):")
    for cid, title, ctype in set(channels_found):
        print(f"    - Title: '{title}' | Type: {ctype} | Chat ID: {cid}")

    # Auto update if channel found
    best_candidate = channels_found[-1][0]
    best_title = channels_found[-1][1]
    cfg["channel_id"] = str(best_candidate)

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    print(f"\n[SUCCESS] Automatically saved Channel ID '{best_candidate}' ({best_title}) into config/telegram_config.json!")
    print("[+] Now you can run: python scripts/test_telegram_connection.py to send the verification broadcast card.")

if __name__ == "__main__":
    main()
