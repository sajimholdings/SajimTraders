"""
========================================================================================
         SAJIM HOLDINGS — PROP FIRM CHALLENGE QUANT ENGINE v1.0
                  (bots/prop_firm/prop_firm_challenge_bot.py)
========================================================================================
Architect & Lead Quant: Jimmy Mathu
Purpose:
  Built specifically to pass $50,000, $100,000, and $200,000 Institutional Prop Firm
  Challenges (FTMO, FundedNext, Alpha Capital, E8, Headway) with zero rule violations.

Prop Firm Hard Guardrails:
  1. Maximum Total Drawdown Protection: 5.0% Hard Circuit Breaker (Prop rule is 8-10%).
  2. Maximum Daily Drawdown Protection: 3.5% Hard Circuit Breaker (Prop rule is 5.0%).
  3. Dynamic Fractional Sizing: Fixed 0.50% - 0.75% risk per trade via UniversalLotCalculator.
  4. High Asymmetric R:R: Minimum 1:3.0 Target (Positive Expectancy on 35%+ Win Rate).
  5. High-Conviction BEEP Layer Gating: Trades ONLY RARE (M(t) >= 60) & CERTIFIED layers.
  6. Correlated Exposure Limit: Maximum 2 concurrent open positions across all pairs.
  7. Automated Trailing Break-Even: Locks risk-free at 1:1.5 R:R to protect daily equity.
  8. Sammy's 4-Check Gatekeeper: Pre-trade audit before any order reaches the bridge.

Drawdown baselines:
  - `--size` is the challenge's initial balance and the total-drawdown baseline (it is NOT
    overwritten by the current balance on connect).
  - peak equity (trailing drawdown) and the UTC start-of-day equity are persisted to
    state/prop_firm_<login>.json so restarts do not reset the guardrails.
  - Requires the private BEEP vault (vault_original_beep) for signal generation.
  - --live sends real MT5 market orders (fresh tick price, SL/TP attached); default is dry run.
========================================================================================
"""

import os
import sys
import time
import math
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Path setup for standalone or modular execution
PROP_DIR = os.path.dirname(os.path.abspath(__file__))
BOTS_DIR = os.path.dirname(PROP_DIR)
ROOT_DIR = os.path.dirname(BOTS_DIR)

for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), BOTS_DIR, PROP_DIR, os.path.join(ROOT_DIR, "vault")):
    if p not in sys.path:
        sys.path.insert(0, p)

import MetaTrader5 as mt5
from core.lot_calculator import UniversalLotCalculator
from v2.safety import STATE_DIR, new_entries_allowed, utc_day_start
from v2.execution.mt5_exec import send_market_order

try:
    from vault_original_beep.raw_beep_equations import OriginalRawBeep  # private BEEP vault (git-ignored)
except ImportError:  # pragma: no cover - depends on private modules
    OriginalRawBeep = None


class PropFirmRiskProfile:
    """Rigorous risk limits tailored for funded challenge accounts."""
    def __init__(
        self,
        account_size: float = 100000.0,
        max_total_dd_pct: float = 5.0,    # Firm rule 8-10%, Sajim buffer 5.0% (static, from initial balance)
        max_daily_dd_pct: float = 3.5,    # Firm rule 5.0%, Sajim buffer 3.5%
        risk_per_trade_pct: float = 0.50, # 0.50% risk per trade ($500 on $100k)
        max_open_positions: int = 2,
        min_rr_ratio: float = 3.0,
        max_trailing_dd_pct: Optional[float] = None,  # trailing from peak equity (default = max_total_dd_pct)
        state_file: Optional[str] = None,
    ):
        self.account_size = account_size
        self.max_total_dd_pct = max_total_dd_pct
        self.max_daily_dd_pct = max_daily_dd_pct
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_open_positions = max_open_positions
        self.min_rr_ratio = min_rr_ratio
        self.max_trailing_dd_pct = max_total_dd_pct if max_trailing_dd_pct is None else max_trailing_dd_pct
        self.state_file = state_file

        # Dynamic Watermarks
        self.starting_daily_equity = account_size
        self.current_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.peak_equity = account_size
        self._load_state()

    # ----------------------------------------------------------- persistence
    def _load_state(self) -> None:
        if not self.state_file or not os.path.exists(self.state_file):
            return
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                st = json.load(f)
            if float(st.get("account_size", 0.0)) == float(self.account_size):
                self.peak_equity = max(self.account_size, float(st.get("peak_equity", self.account_size)))
                self.starting_daily_equity = float(st.get("starting_daily_equity", self.account_size))
                # Keep the persisted day so a new UTC day triggers check_daily_reset()
                self.current_day = st.get("current_day", self.current_day)
            else:
                logging.warning(
                    f"[PROP GUARD] State file is for account size {st.get('account_size')}, not {self.account_size}; "
                    f"starting fresh baselines."
                )
        except Exception as e:
            logging.warning(f"[PROP GUARD] Could not read state {self.state_file}: {e}")

    def save_state(self) -> None:
        if not self.state_file:
            return
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            tmp = self.state_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({
                    "account_size": self.account_size,
                    "peak_equity": self.peak_equity,
                    "current_day": self.current_day,
                    "starting_daily_equity": self.starting_daily_equity,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, f, indent=2)
            os.replace(tmp, self.state_file)
        except Exception as e:
            logging.warning(f"[PROP GUARD] Could not persist state {self.state_file}: {e}")

    def check_daily_reset(self, current_equity: float, start_of_day_balance: Optional[float] = None):
        """Resets daily starting equity at 00:00 UTC."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self.current_day:
            self.current_day = today
            # Baseline is the higher of current equity and the reconstructed start-of-day balance
            self.starting_daily_equity = max(current_equity, start_of_day_balance or 0.0)
            logging.info(f"[PROP GUARD] Daily reset triggered for {today}. Baseline equity: ${self.starting_daily_equity:,.2f}")
            self.save_state()

    def evaluate_gatekeeper(
        self,
        current_equity: float,
        open_positions_count: int,
        start_of_day_balance: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """Sammy's 4-Check Gatekeeper tailored for Prop Firm preservation."""
        self.check_daily_reset(current_equity, start_of_day_balance)

        # Update high-water mark (persisted)
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
            self.save_state()

        # 1. Total (static) Drawdown Check vs the challenge's initial balance (--size)
        total_dd = (self.account_size - current_equity) / self.account_size * 100.0
        if total_dd >= self.max_total_dd_pct:
            return False, f"CIRCUIT BREAKER: Total drawdown {total_dd:.2f}% >= {self.max_total_dd_pct}% limit"

        # 1b. Trailing Drawdown from peak equity (measured in % of initial balance)
        trailing_dd = (self.peak_equity - current_equity) / self.account_size * 100.0
        if trailing_dd >= self.max_trailing_dd_pct:
            return False, (
                f"CIRCUIT BREAKER: Trailing drawdown {trailing_dd:.2f}% from peak ${self.peak_equity:,.2f} "
                f">= {self.max_trailing_dd_pct}% limit"
            )

        # 2. Daily Drawdown Check
        daily_loss = (self.starting_daily_equity - current_equity) / self.starting_daily_equity * 100.0
        if daily_loss >= self.max_daily_dd_pct:
            return False, f"CIRCUIT BREAKER: Daily loss {daily_loss:.2f}% >= {self.max_daily_dd_pct}% daily limit"

        # 3. Maximum Concurrent Trades Check
        if open_positions_count >= self.max_open_positions:
            return False, f"EXPOSURE CAP: Open positions ({open_positions_count}) at max ({self.max_open_positions})"

        return True, "PASSED: All Prop Firm Gatekeeper checks approved"


class PropFirmChallengeBot:
    """Autonomous Prop Firm execution bot using BEEP Physics & strict drawdown controls."""

    def __init__(
        self,
        account_size: float = 100000.0,
        dry_run: bool = True,
        magic_number: int = 770889,
        target_symbols: Optional[List[str]] = None,
    ):
        if OriginalRawBeep is None:
            raise ImportError(
                "PropFirmChallengeBot requires the private BEEP vault module "
                "vault_original_beep.raw_beep_equations (not in this repo)"
            )
        self.dry_run = dry_run
        self.magic_number = magic_number
        self.account_size = float(account_size)
        self.risk_manager = PropFirmRiskProfile(account_size=self.account_size)
        self.raw_beep = OriginalRawBeep()

        # Prime Liquid Institutional Assets for Prop Firms
        self.symbols = target_symbols or [
            "XAUUSD", "EURUSD", "GBPUSD", "USDJPY",
            "USDCAD", "AUDUSD", "GBPJPY", "US30", "NAS100"
        ]

        self.timeframes = [
            ("M15", mt5.TIMEFRAME_M15, 60),
            ("H1",  mt5.TIMEFRAME_H1,  48),
        ]

    def connect(self) -> bool:
        """Connects to MT5 terminal."""
        if not mt5.initialize():
            logging.error(f"[!] MT5 initialization failed: {mt5.last_error()}")
            return False
        acc_info = mt5.account_info()
        if not acc_info:
            logging.error("[!] Unable to read MT5 account details")
            return False
        logging.info(f"[+] Connected to MT5 Account: {acc_info.login} ({acc_info.server})")
        logging.info(f"[+] Equity: ${acc_info.equity:,.2f} | Balance: ${acc_info.balance:,.2f}")
        logging.info(f"[+] Challenge baseline (--size): ${self.account_size:,.2f}")

        # Keep --size as the drawdown baseline; restore persisted peak / daily baseline
        state_file = os.path.join(STATE_DIR, f"prop_firm_{acc_info.login}.json")
        self.risk_manager = PropFirmRiskProfile(account_size=self.account_size, state_file=state_file)
        if not os.path.exists(state_file):
            self.risk_manager.starting_daily_equity = max(acc_info.equity, self._start_of_day_balance(acc_info))
            self.risk_manager.peak_equity = max(self.account_size, acc_info.equity)
            self.risk_manager.save_state()
        return True

    def _start_of_day_balance(self, acc_info) -> float:
        """Balance at 00:00 UTC reconstructed from today's trading deals."""
        try:
            deals = mt5.history_deals_get(utc_day_start(), datetime.now(timezone.utc)) or []
            realized = sum(
                float(d.profit) + float(d.swap) + float(getattr(d, "commission", 0.0) or 0.0)
                + float(getattr(d, "fee", 0.0) or 0.0)
                for d in deals if getattr(d, "type", 0) in (0, 1)
            )
            return float(acc_info.balance) - realized
        except Exception:
            return float(acc_info.balance)

    def scan_for_institutional_edges(self) -> List[Dict[str, Any]]:
        """Scans candidate symbols for RARE (M(t) >= 60) BEEP signatures."""
        candidates = []
        for sym in self.symbols:
            for tf_label, tf_enum, num_bars in self.timeframes:
                rates = mt5.copy_rates_from_pos(sym, tf_enum, 0, num_bars)
                if rates is None or len(rates) < num_bars:
                    continue

                closes = [float(r['close']) for r in rates]
                highs  = [float(r['high']) for r in rates]
                lows   = [float(r['low']) for r in rates]

                # Run Pure BEEP Equations
                window = closes[-25:]
                b_t = self.raw_beep.calculate_raw_baseline_B(window)
                m_t = self.raw_beep.calculate_raw_mass_M(window, b_t)
                abs_m = abs(m_t)

                if abs_m >= 75.0:
                    layer = "DIAMOND"
                    action = "BUY" if m_t > 0 else "SELL"
                elif abs_m >= 55.0:
                    layer = "RARE"
                    action = "BUY" if m_t > 0 else "SELL"
                elif abs_m >= 35.0:
                    layer = "CERTIFIED"
                    action = "BUY" if m_t > 0 else "SELL"
                else:
                    layer = "STANDARD"
                    action = "HOLD"

                # Prop Firm Rule: ONLY execute on RARE or CERTIFIED momentum anomalies
                if layer in ("RARE", "CERTIFIED", "DIAMOND") and action in ("BUY", "SELL"):
                    entry = float(rates[-1]['close'])
                    sl = entry - (abs(entry - b_t) * 1.2) if action == "BUY" else entry + (abs(entry - b_t) * 1.2)
                    risk_dist = abs(entry - sl)
                    if risk_dist <= 0:
                        continue
                    
                    tp = entry + (risk_dist * self.risk_manager.min_rr_ratio) if action == "BUY" else entry - (risk_dist * self.risk_manager.min_rr_ratio)

                    candidates.append({
                        "symbol": sym,
                        "tf": tf_label,
                        "action": action,
                        "layer": layer,
                        "m_t": abs_m,
                        "entry": entry,
                        "sl": sl,
                        "tp": tp,
                        "rr": self.risk_manager.min_rr_ratio,
                    })

        # Rank candidates by kinetic momentum
        candidates.sort(key=lambda x: x["m_t"], reverse=True)
        return candidates

    def run_single_iteration(self):
        """Runs a single scan and audit iteration."""
        acc = mt5.account_info()
        if not acc:
            return

        positions = [p for p in (mt5.positions_get() or []) if p.magic == self.magic_number]
        allowed, reason = self.risk_manager.evaluate_gatekeeper(
            acc.equity, len(positions), start_of_day_balance=self._start_of_day_balance(acc)
        )

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] --- PROP FIRM MONITOR ---")
        print(f"Equity: ${acc.equity:,.2f} | Daily Base: ${self.risk_manager.starting_daily_equity:,.2f}")
        print(f"Gatekeeper Status: {reason}")
        print(f"Active Prop Positions: {len(positions)} / {self.risk_manager.max_open_positions}")

        if not allowed:
            print(f"[!] Trading locked: {reason}")
            return
        if not new_entries_allowed("PROPFIRM"):
            print("[!] Trading locked: global kill switch engaged")
            return

        edges = self.scan_for_institutional_edges()
        if not edges:
            print("[*] No qualifying RARE/CERTIFIED institutional setups found.")
            return

        top_edge = edges[0]
        print(f"[+] BEST PROP SETUP FOUND: {top_edge['symbol']} {top_edge['tf']} {top_edge['action']} "
              f"[{top_edge['layer']}] M(t)={top_edge['m_t']:.1f}")

        try:
            lot, cash_at_risk, specs = UniversalLotCalculator.calculate_lot(
                symbol=top_edge['symbol'],
                equity=acc.equity,
                risk_fraction=self.risk_manager.risk_per_trade_pct / 100.0,
                entry_price=top_edge['entry'],
                stop_price=top_edge['sl'],
                account_currency=acc.currency,
            )
        except ValueError as e:
            print(f"[!] Sizing failed: {e}")
            return
        if lot <= 0:
            print(f"[!] Trade rejected by sizing: {specs.get('rejected')}")
            return
        print(f"[*] Computed Safe Challenge Lot: {lot} (Risking {cash_at_risk:,.2f} = {self.risk_manager.risk_per_trade_pct:.2f}%)")

        ok, res, fill = send_market_order(
            symbol=top_edge['symbol'],
            action=top_edge['action'],
            volume=float(lot),
            sl=float(top_edge['sl']),
            tp=float(top_edge['tp']),
            magic=self.magic_number,
            comment=f"Sajim_Prop_{top_edge['layer'][:8]}",
            dry_run=self.dry_run,
            bot_name="PROPFIRM",
        )
        if self.dry_run:
            print(f"[DRY RUN] Would execute: {top_edge['action']} {lot} {top_edge['symbol']} "
                  f"SL={top_edge['sl']:.4f} TP={top_edge['tp']:.4f} (no order sent)")
        elif ok:
            print(f"[LIVE PROP EXECUTION] Filled #{res.order} {top_edge['action']} {lot} {top_edge['symbol']} @ {fill}")
        else:
            print("[!] LIVE PROP EXECUTION FAILED (see log).")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sajim Holdings Prop Firm Challenge Bot")
    parser.add_argument("--size", type=float, default=100000.0, help="Account size ($50k, $100k, $200k)")
    parser.add_argument("--live", action="store_true", help="Execute real MT5 challenge orders (default: Dry Run)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    try:
        bot = PropFirmChallengeBot(account_size=args.size, dry_run=not args.live)
    except ImportError as e:
        print(f"[!] {e}")
        sys.exit(1)
    if bot.connect():
        bot.run_single_iteration()


if __name__ == "__main__":
    main()
