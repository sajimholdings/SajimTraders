"""
Shared MT5 auto-login helper.

Builds the kwargs for mt5.initialize() to LAUNCH the terminal and log in
automatically, from (in priority order):
  1. environment: MT5_TERMINAL_PATH, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER
  2. config/broker_config.json (active_account + terminal_path + password + server)

Returns {} when nothing is configured (caller then just attaches to a running terminal).
"""

import os
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_login_kwargs() -> dict:
    path = os.environ.get("MT5_TERMINAL_PATH")
    login = os.environ.get("MT5_LOGIN")
    password = os.environ.get("MT5_PASSWORD")
    server = os.environ.get("MT5_SERVER")

    if not (path and login and password):
        try:
            cfg_path = os.path.join(ROOT_DIR, "config", "broker_config.json")
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            path = path or cfg.get("terminal_path")
            login = login or str(cfg.get("active_account", ""))
            password = password or cfg.get("password")
            server = server or cfg.get("server")
        except Exception:
            pass

    kwargs = {}
    if path:
        kwargs["path"] = path
    if login:
        kwargs["login"] = int(login)
        if password:
            kwargs["password"] = password
        if server:
            kwargs["server"] = server
    return kwargs
