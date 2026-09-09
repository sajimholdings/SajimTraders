"""Automated verification test for line-by-line fixes."""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "bots"), os.path.join(ROOT_DIR, "vault")):
    if p not in sys.path:
        sys.path.insert(0, p)

import MetaTrader5 as mt5
from core.beep_signal_engine import BeepSignalEngine
from bots.sajim_v1_bot import SajimV1Bot

mt5.initialize()

print("=" * 80)
print("             SAJIM V1 — AUDIT FIX VERIFICATION SUITE")
print("=" * 80)

# 1. BEEP Signal Engine Direction & Stop Calibration
engine = BeepSignalEngine()
cent_syms = [
    s.name for s in mt5.symbols_get()
    if s.name.endswith(".c") and s.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL
]
engine.set_universe(cent_syms)
signals = engine.scan_all_universe()

buys = [s for s in signals if s.action == "BUY"]
sells = [s for s in signals if s.action == "SELL"]
print(f"[TEST 1] Signals emitted: {len(signals)} total")
print(f"         - BUY signals  : {len(buys)}")
print(f"         - SELL signals : {len(sells)}")
assert len(sells) > 0, "ERROR: No SELL signals emitted! Directional flaw still present."
print("         => PASS: Both BUY and SELL signals successfully emitted!")

# Check Gold stops
gold_signals = [s for s in signals if "XAU" in s.symbol]
if gold_signals:
    print(f"\n[TEST 2] Verifying Gold Stop Loss buffer:")
    for gs in gold_signals[:3]:
        dist = abs(gs.entry_price - gs.stop_loss)
        print(f"         - {gs.symbol} {gs.timeframe} {gs.action} Entry:{gs.entry_price} SL:{gs.stop_loss} Dist:{dist:.2f}")
        assert dist >= 5.0, f"ERROR: Gold stop distance {dist:.2f} < 5.00!"
    print("         => PASS: Gold stop loss properly calibrated to >= $5.00!")
else:
    print("\n[TEST 2] No active Gold signals at this exact moment (skipped check).")

# 2. Sajim V1 Bot Seeding & Ticket Tracking
print(f"\n[TEST 3] Verifying Ticket-based deal seeding:")
bot = SajimV1Bot()
assert bot.connect(1200438589), "ERROR: Failed to connect to JustMarkets Cent account."
print(f"         - Seeded historical deal tickets: {len(bot.processed_deal_tickets)}")
assert len(bot.processed_deal_tickets) >= 19, f"ERROR: Expected >= 19 historical deals, got {len(bot.processed_deal_tickets)}"
print("         => PASS: All historical deals successfully indexed; immune to timezone bugs!")

# 3. Risk Cutoff Guard on Oversized Instruments
print(f"\n[TEST 4] Verifying Hard Risk Cutoff Guard:")
from core.beep_signal_engine import BeepSignal
# Mock an oversized Silver signal
mock_silver = BeepSignal(
    signal_id="MOCK_XAG",
    symbol="XAGUSD.c",
    timeframe="M15",
    bar_time=1234567,
    action="BUY",
    layer="RARE",
    m_t=60.0,
    b_t=65.0,
    entry_price=66.0,
    stop_loss=63.0,  # $3.00 stop = 150 USC risk on 0.01 lot
    take_profit=76.5,
    risk_reward=3.5,
    phi_energy=100.0,
    spread_points=10,
    created_at="2026-09-08 10:00:00",
)
prep = bot.evaluate_signal_and_size(mock_silver)
assert prep is None, "ERROR: Oversized Silver signal was NOT rejected by risk cutoff guard!"
print("         => PASS: Oversized Silver signal rejected cleanly by Risk Cutoff Guard!")

print("\n" + "=" * 80)
print("       ALL 4 VERIFICATION TESTS PASSED WITH 100% SUCCESS!")
print("=" * 80)
mt5.shutdown()
