"""
========================================================================================
       SAJIM QUANT LABS — EMPIRICAL SIGNAL TRUTH TESTER & FORWARD AUDITOR
                           (core/signal_truth_tester.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Concept & Vision:
  - Captures and logs every raw signal generated across all monitored assets (Forex,
    Metals, Indices, and Crypto like BTCUSD).
  - Tracks live forward evolution (MFE, MAE, R-Multiple, Hit Rates for TP1, TP2, TP3, SL).
  - Completely separates raw anomaly detection from execution risk.
  - Builds an empirical truth database to dynamically qualify and promote new assets
    into the live trading catalogue with zero curve-fitting.
========================================================================================
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import MetaTrader5 as mt5

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
VAULT_DIR = os.path.join(ROOT_DIR, "vault")
os.makedirs(VAULT_DIR, exist_ok=True)

VAULT_FILE = os.path.join(VAULT_DIR, "signal_truth_vault.json")
SCOREBOARD_FILE = os.path.join(VAULT_DIR, "signal_truth_scoreboard.json")

logger = logging.getLogger("SignalTruthTester")


class SignalTruthTester:
    """
    Continuous Forward-Testing & Telemetry Engine.
    Monitors signals as they age in live market time to verify ground-truth profitability.
    """

    TIMEFRAME_MAP = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }

    def __init__(self, max_forward_bars: int = 60):
        self.max_forward_bars = max_forward_bars
        self.records: Dict[str, Dict[str, Any]] = {}
        self.load_vault()

    def load_vault(self) -> None:
        """Loads persistent forward signals from vault."""
        if os.path.exists(VAULT_FILE):
            try:
                with open(VAULT_FILE, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load truth vault: {e}")
                self.records = {}

    def save_vault(self) -> None:
        """Persists truth vault to disk."""
        try:
            with open(VAULT_FILE, "w", encoding="utf-8") as f:
                json.dump(self.records, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save truth vault: {e}")

    def register_signal(
        self,
        strategy_name: str,
        symbol: str,
        timeframe: str,
        action: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        risk_reward: float = 2.0,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Registers an observed signal into the forward tracking database.
        """
        now = datetime.now()
        clean_sym = symbol.replace(".c", "").replace("_c", "")
        signal_id = f"{strategy_name}_{clean_sym}_{timeframe}_{action}_{now.strftime('%Y%m%d_%H%M%S')}"

        # Deduplicate signals within debounce window (300 seconds)
        for existing_id, rec in self.records.items():
            if (
                rec["strategy"] == strategy_name
                and rec["symbol"] == symbol
                and rec["timeframe"] == timeframe
                and rec["action"] == action
            ):
                try:
                    created = datetime.strptime(rec["created_at"], "%Y-%m-%d %H:%M:%S")
                    if (now - created).total_seconds() < 300:  # 5 min debounce
                        return existing_id
                except Exception:
                    pass

        tick = mt5.symbol_info_tick(symbol)
        server_epoch = int(tick.time) if tick else int(datetime.now().timestamp())

        risk_dist = abs(entry_price - stop_loss)
        if risk_dist <= 0:
            risk_dist = entry_price * 0.0010

        is_buy = action == "BUY"
        tp1 = (entry_price + 1.0 * risk_dist) if is_buy else (entry_price - 1.0 * risk_dist)
        tp2 = (entry_price + 2.0 * risk_dist) if is_buy else (entry_price - 2.0 * risk_dist)
        tp3 = take_profit

        record = {
            "signal_id": signal_id,
            "strategy": strategy_name,
            "symbol": symbol,
            "clean_symbol": clean_sym,
            "timeframe": timeframe,
            "action": action,
            "entry_price": float(entry_price),
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "tp1": float(tp1),
            "tp2": float(tp2),
            "tp3": float(tp3),
            "risk_dist": float(risk_dist),
            "risk_reward": float(risk_reward),
            "confidence": float(confidence),
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "created_server_time": server_epoch,
            "status": "ACTIVE",              # ACTIVE, RESOLVED_TP1, RESOLVED_TP2, RESOLVED_TP3, RESOLVED_SL, EXPIRED
            "outcome": None,
            "pnl_r": 0.0,
            "mfe_price": float(entry_price), # Maximum Favorable Excursion
            "mae_price": float(entry_price), # Maximum Adverse Excursion
            "mfe_r": 0.0,
            "mae_r": 0.0,
            "bars_monitored": 0,
            "tp1_hit": False,
            "tp2_hit": False,
            "tp3_hit": False,
            "sl_hit": False,
            "resolved_at": None,
            "metadata": metadata or {},
        }

        self.records[signal_id] = record
        self.save_vault()
        logger.info(f"[🔬 TRUTH LAB LOGGED] #{signal_id} {action} {symbol} ({timeframe}) @ {entry_price:.5f} | SL: {stop_loss:.5f} | TP3: {take_profit:.5f}")
        return signal_id

    def audit_forward_signals(self) -> Dict[str, Any]:
        """
        Queries MT5 for subsequent price action on all ACTIVE signals,
        computes MFE, MAE, and marks resolution (TP/SL/Expiry).
        """
        active_records = [r for r in self.records.values() if r["status"] == "ACTIVE"]
        if not active_records:
            return {"updated": 0, "active_remaining": 0}

        now = datetime.now()
        updated_count = 0

        for rec in active_records:
            sym = rec["symbol"]
            tf_label = rec["timeframe"]
            tf = self.TIMEFRAME_MAP.get(tf_label, mt5.TIMEFRAME_M15)
            created_dt = datetime.strptime(rec["created_at"], "%Y-%m-%d %H:%M:%S")

            rates = mt5.copy_rates_from_pos(sym, tf, 0, min(self.max_forward_bars + 10, 80))
            if rates is None or len(rates) == 0:
                continue

            created_epoch = rec.get("created_server_time", 0)
            if created_epoch == 0:
                try:
                    created_dt = datetime.strptime(rec["created_at"], "%Y-%m-%d %H:%M:%S")
                    created_epoch = int(created_dt.timestamp()) + 3 * 3600
                except Exception:
                    created_epoch = 0

            entry = rec["entry_price"]
            sl = rec["stop_loss"]
            tp1 = rec["tp1"]
            tp2 = rec["tp2"]
            tp3 = rec["tp3"]
            risk_dist = rec["risk_dist"]
            is_buy = rec["action"] == "BUY"

            mfe_price = rec["mfe_price"]
            mae_price = rec["mae_price"]
            bars_count = 0
            resolved = False
            outcome = None
            final_pnl_r = 0.0

            # 1. First audit against live tick price
            live_tick = mt5.symbol_info_tick(sym)
            if live_tick:
                live_price = float(live_tick.bid if is_buy else live_tick.ask)
                if is_buy:
                    mfe_price = max(mfe_price, live_price)
                    mae_price = min(mae_price, live_price)
                    if live_price >= tp3:
                        resolved = True
                        outcome = "WIN_TP3"
                        final_pnl_r = rec["risk_reward"]
                    elif live_price <= sl:
                        resolved = True
                        outcome = "LOSS_SL"
                        final_pnl_r = -1.0
                else:
                    mfe_price = min(mfe_price, live_price)
                    mae_price = max(mae_price, live_price)
                    if live_price <= tp3:
                        resolved = True
                        outcome = "WIN_TP3"
                        final_pnl_r = rec["risk_reward"]
                    elif live_price >= sl:
                        resolved = True
                        outcome = "LOSS_SL"
                        final_pnl_r = -1.0

            # 2. Audit against subsequent completed bars (strictly bar open time > signal server epoch)
            if not resolved:
                for bar in rates:
                    bar_time = int(bar["time"])
                    if bar_time <= created_epoch:
                        continue

                    bars_count += 1
                    b_high = float(bar["high"])
                    b_low = float(bar["low"])

                    # Track MFE & MAE
                    if is_buy:
                        mfe_price = max(mfe_price, b_high)
                        mae_price = min(mae_price, b_low)
                        mfe_r = (mfe_price - entry) / risk_dist
                        mae_r = (entry - mae_price) / risk_dist

                        # Check TP triggers
                        if b_high >= tp1 and not rec["tp1_hit"]:
                            rec["tp1_hit"] = True
                        if b_high >= tp2 and not rec["tp2_hit"]:
                            rec["tp2_hit"] = True
                        if b_high >= tp3:
                            rec["tp3_hit"] = True
                            resolved = True
                            outcome = "WIN_TP3"
                            final_pnl_r = rec["risk_reward"]
                            break

                        # Check SL trigger
                        if b_low <= sl:
                            rec["sl_hit"] = True
                            resolved = True
                            outcome = "LOSS_SL"
                            final_pnl_r = -1.0
                            break
                    else:  # SELL
                        mfe_price = min(mfe_price, b_low)
                        mae_price = max(mae_price, b_high)
                        mfe_r = (entry - mfe_price) / risk_dist
                        mae_r = (mae_price - entry) / risk_dist

                        # Check TP triggers
                        if b_low <= tp1 and not rec["tp1_hit"]:
                            rec["tp1_hit"] = True
                        if b_low <= tp2 and not rec["tp2_hit"]:
                            rec["tp2_hit"] = True
                        if b_low <= tp3:
                            rec["tp3_hit"] = True
                            resolved = True
                            outcome = "WIN_TP3"
                            final_pnl_r = rec["risk_reward"]
                            break

                        # Check SL trigger
                        if b_high >= sl:
                            rec["sl_hit"] = True
                            resolved = True
                            outcome = "LOSS_SL"
                            final_pnl_r = -1.0
                            break

                    # Max horizon expiration
                    if bars_count >= self.max_forward_bars:
                        resolved = True
                        outcome = "EXPIRED"
                        cur_close = float(bar["close"])
                        cur_pnl = ((cur_close - entry) / risk_dist) if is_buy else ((entry - cur_close) / risk_dist)
                        final_pnl_r = float(cur_pnl)
                        break

            rec["mfe_price"] = float(mfe_price)
            rec["mae_price"] = float(mae_price)
            rec["mfe_r"] = round(float((mfe_price - entry) / risk_dist if is_buy else (entry - mfe_price) / risk_dist), 2)
            rec["mae_r"] = round(float((entry - mae_price) / risk_dist if is_buy else (mae_price - entry) / risk_dist), 2)
            rec["bars_monitored"] = bars_count

            if resolved:
                rec["status"] = f"RESOLVED_{outcome}"
                rec["outcome"] = outcome
                rec["pnl_r"] = round(final_pnl_r, 2)
                rec["resolved_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"[🏁 TRUTH LAB RESOLVED] #{rec['signal_id']} -> {outcome} | PnL: {final_pnl_r:+.2f}R | MFE: +{rec['mfe_r']:.2f}R | MAE: -{rec['mae_r']:.2f}R")

            updated_count += 1

        self.save_vault()
        self.generate_scoreboard()
        active_remaining = sum(1 for r in self.records.values() if r["status"] == "ACTIVE")
        return {"updated": updated_count, "active_remaining": active_remaining}

    def generate_scoreboard(self) -> Dict[str, Any]:
        """
        Computes aggregate forward accuracy metrics per asset and per strategy.
        Identifies eligible assets for promotion to Tier 1 Live Whitelist.
        """
        scoreboard: Dict[str, Any] = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_signals_tracked": len(self.records),
            "by_asset": {},
            "by_strategy": {},
            "promoted_catalogue": [],
        }

        # Aggregate by asset
        asset_stats: Dict[str, List[Dict[str, Any]]] = {}
        for rec in self.records.values():
            sym = rec["clean_symbol"]
            asset_stats.setdefault(sym, []).append(rec)

        for sym, recs in asset_stats.items():
            resolved = [r for r in recs if r["status"] != "ACTIVE"]
            wins = [r for r in resolved if r["pnl_r"] > 0]
            losses = [r for r in resolved if r["pnl_r"] < 0]

            total_n = len(recs)
            resolved_n = len(resolved)
            win_n = len(wins)
            loss_n = len(losses)

            win_rate = (win_n / resolved_n * 100.0) if resolved_n > 0 else 0.0
            gross_win_r = sum(r["pnl_r"] for r in wins)
            gross_loss_r = abs(sum(r["pnl_r"] for r in losses))
            pf = (gross_win_r / gross_loss_r) if gross_loss_r > 0 else (9.99 if gross_win_r > 0 else 0.0)
            avg_mfe = sum(r["mfe_r"] for r in recs) / total_n if total_n > 0 else 0.0
            avg_mae = sum(r["mae_r"] for r in recs) / total_n if total_n > 0 else 0.0
            expectancy = sum(r["pnl_r"] for r in resolved) / resolved_n if resolved_n > 0 else 0.0

            # Dynamic Qualification Tier
            if resolved_n >= 5 and win_rate >= 60.0 and pf >= 2.0:
                tier = "TIER_1_PRIME_PROMOTED"
                scoreboard["promoted_catalogue"].append(sym)
            elif resolved_n >= 3 and win_rate >= 50.0 and pf >= 1.2:
                tier = "PROBATION_WATCHLIST"
            elif resolved_n >= 3 and (win_rate < 40.0 or pf < 0.9):
                tier = "BENCHED_BLEEDER"
            else:
                tier = "INCUBATING_DATA_GATHERING"

            scoreboard["by_asset"][sym] = {
                "total_signals": total_n,
                "resolved": resolved_n,
                "wins": win_n,
                "losses": loss_n,
                "win_rate_pct": round(win_rate, 1),
                "profit_factor": round(pf, 2),
                "avg_mfe_r": round(avg_mfe, 2),
                "avg_mae_r": round(avg_mae, 2),
                "expectancy_r": round(expectancy, 2),
                "qualification_tier": tier,
            }

        try:
            with open(SCOREBOARD_FILE, "w", encoding="utf-8") as f:
                json.dump(scoreboard, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write scoreboard: {e}")

        return scoreboard


# Global Singleton
_truth_tester_instance: Optional[SignalTruthTester] = None


def get_signal_truth_tester() -> SignalTruthTester:
    global _truth_tester_instance
    if _truth_tester_instance is None:
        _truth_tester_instance = SignalTruthTester()
    return _truth_tester_instance
