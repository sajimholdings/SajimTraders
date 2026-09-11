"""
========================================================================================
        SAJIM HOLDINGS — V2 SIGNAL GENERATOR (scripts/signal_generator.py)
========================================================================================
Runs the V2 cartridge engine continuously in SIGNAL-ONLY mode: scans the market,
broadcasts, and publishes signals to Supabase. It NEVER places orders — execution
happens per-account via each client's bridge worker (autopilot).

Requires a running MT5 terminal (to read symbol data). Set SIGNAL_INTERVAL (seconds)
to control the scan cadence (default 60).
"""

import os
import sys
import time
import logging

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "v2"), os.path.join(ROOT_DIR, "bots")):
    if p not in sys.path:
        sys.path.insert(0, p)

import MetaTrader5 as mt5
from v2.sajim_v2_dual_bot import SajimV2DualBot
from core.mt5_login import get_login_kwargs

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SIGNAL] %(message)s")
log = logging.getLogger("SignalGenerator")


def main():
    os.environ["MUTE_TELEGRAM"] = "1"  # signal generator publishes to Supabase, not Telegram
    kwargs = get_login_kwargs()
    ok = mt5.initialize(**kwargs) if kwargs else mt5.initialize()
    if not ok:
        time.sleep(2)
        ok = mt5.initialize(**kwargs) if kwargs else mt5.initialize()
    if not ok:
        log.error(f"MT5 init failed: {mt5.last_error()}")
        return 1

    bot = SajimV2DualBot(dry_run=True)

    # Build the tradable universe from the whitelist (attach to running terminal only).
    bot.universe = []
    for target in bot.target_symbols:
        for cand in (target, f"{target}.c", f"{target}_c", f"{target}c"):
            si = mt5.symbol_info(cand)
            if si and si.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                if not si.visible:
                    mt5.symbol_select(cand, True)
                bot.universe.append(cand)
                break

    # SIGNAL-ONLY: never execute orders here.
    bot.execute_signal = lambda sig: False

    log.info(f"V2 signal generator running. Universe ({len(bot.universe)}): {bot.universe}")

    interval = float(os.environ.get("SIGNAL_INTERVAL", "60"))
    while True:
        try:
            bot.scan_and_evaluate()
        except Exception as e:
            log.warning(f"scan error: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
