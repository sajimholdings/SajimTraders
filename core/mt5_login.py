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


# ---------------------------------------------------------------------------
# Shared account-switch helper (used by V1, V2 dual bot and the dual orchestrator)
# ---------------------------------------------------------------------------
def load_broker_config() -> dict:
    """Reads config/broker_config.json (git-ignored). Returns {} if absent/unreadable."""
    try:
        cfg_path = os.path.join(ROOT_DIR, "config", "broker_config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def resolve_target_account(target_account=None, use_configured_default: bool = True):
    """
    Explicit target first, then MT5_LOGIN env, then broker_config active_account.
    Returns an int login or None (= attach to whatever account the terminal has).
    """
    if target_account:
        return int(target_account)
    if not use_configured_default:
        return None
    env_login = os.environ.get("MT5_LOGIN")
    if env_login:
        return int(env_login)
    active = load_broker_config().get("active_account")
    return int(active) if active else None


def credentials_for(account) -> tuple:
    """
    (password, server) for an account, from env (when MT5_LOGIN matches) or
    broker_config.json (per-account `accounts` map, then top-level when it is the
    active_account). Never falls back to hard-coded servers or accounts.
    """
    if account is None:
        return None, None
    acc_str = str(account)
    if os.environ.get("MT5_LOGIN") == acc_str:
        return os.environ.get("MT5_PASSWORD"), os.environ.get("MT5_SERVER")
    cfg = load_broker_config()
    per_acc = (cfg.get("accounts") or {}).get(acc_str) or {}
    if per_acc:
        return per_acc.get("password", cfg.get("password")), per_acc.get("server", cfg.get("server"))
    if str(cfg.get("active_account", "")) == acc_str:
        return cfg.get("password"), cfg.get("server")
    return None, None


def ensure_account(mt5, target_account=None, logger=None, use_configured_default: bool = True):
    """
    Ensures the (already initialized) terminal is logged into the target account.
    Returns mt5.account_info() on success, or None if the terminal is on the wrong
    account / login failed (callers must abort).
    """
    log = logger
    target = resolve_target_account(target_account, use_configured_default)
    acc = mt5.account_info()
    if target is None:
        return acc
    if acc is not None and int(acc.login) == target:
        return acc

    password, server = credentials_for(target)
    kwargs = {}
    if password:
        kwargs["password"] = password
    if server:
        kwargs["server"] = server
    if log:
        log.info(f"Target account {target} requested; switching terminal login (server: {server or 'terminal default'})...")
    ok = mt5.login(target, **kwargs)
    acc = mt5.account_info()
    if not ok or acc is None or int(acc.login) != target:
        if log:
            log.critical(
                f"[SECURITY LOCK] Could not log into target account {target} "
                f"(terminal is on {getattr(acc, 'login', None)}): {mt5.last_error()}"
            )
        return None
    return acc
