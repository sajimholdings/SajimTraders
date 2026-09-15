#!/usr/bin/env python3
"""Print Discord setup URLs and validate the local .env config for Sajim Holdings."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if not ENV_PATH.exists():
        return env

    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def build_oauth_url(client_id: str) -> str:
    return (
        "https://discord.com/api/oauth2/authorize"
        f"?client_id={client_id}"
        "&permissions=8"
        "&scope=bot"
    )


def main() -> int:
    env = load_env()

    client_id = env.get("DISCORD_CLIENT_ID", "").strip()
    client_secret = env.get("DISCORD_CLIENT_SECRET", "").strip()
    bot_token = env.get("DISCORD_BOT_TOKEN", "").strip()
    guild_id = env.get("DISCORD_GUILD_ID", "").strip()

    print("SAJIM HOLDINGS DISCORD SETUP CHECK")
    print(f"Env file: {ENV_PATH}")
    print()

    if not client_id or not client_secret:
        print("MISSING: DISCORD_CLIENT_ID / DISCORD_CLIENT_SECRET")
        print("Add them to the local .env before inviting the bot.")
        return 1

    print("✅ OAuth app configured")
    print(f"Client ID: {client_id}")
    print(f"Bot invite URL: {build_oauth_url(client_id)}")
    print()

    if not bot_token or bot_token.startswith("PASTE_"):
        print("⚠️ Bot token is still a placeholder. Replace DISCORD_BOT_TOKEN in .env")
    else:
        print("✅ Bot token is present")

    if not guild_id or guild_id.startswith("PASTE_"):
        print("⚠️ Guild ID is still a placeholder. Replace DISCORD_GUILD_ID in .env")
    else:
        print("✅ Guild ID is present")

    print()
    print("Next steps:")
    print("1. Open the OAuth URL above and add the bot to the SAJIM server.")
    print("2. In the Discord Developer Portal, enable Server Members Intent.")
    print("3. Create roles and channel restrictions with the bot command flow.")
    print("4. Fill webhook URLs in .env for automated posting.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
