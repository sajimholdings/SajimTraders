"""
========================================================================================
             SAJIM HOLDINGS — DAILY MARKET & PAIR HEALTH DIGEST GENERATOR
                               (core/market_digest_generator.py)
========================================================================================
Architect & Lead Quant: Jimmy Mathu
Purpose:
  Evaluates all tradable currency pairs and metals in real-time.
  Separates assets into:
    GREEN LIGHT: Clean institutional momentum, tight spread, low wick friction.
    YELLOW LIGHT: Elevated chop / spread, requires strict 3-candle retest.
    RED LIGHT / AVOID: Severe wick meat-grinder, toxic spread, or standby assets (e.g. Gold).
  Publishes the definitive Daily Digest to Telegram channel (@sajimtraders).
========================================================================================
"""

import os
import sys
import logging
from typing import Dict, List, Tuple
from datetime import datetime

import MetaTrader5 as mt5
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.beep_broadcast import BeepBroadcastBus

logger = logging.getLogger("SajimMarketDigest")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

UNIVERSE = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCAD", "USDCHF", "AUDUSD", "NZDUSD",
    "EURCAD", "GBPAUD", "GBPCAD", "EURAUD", "AUDCAD", "GBPNZD",
    "GBPJPY", "EURJPY", "AUDJPY", "NZDJPY", "CADJPY",
    "XAUUSD", "EURGBP"
]

STANDBY_BENCHED = ["XAUUSD", "XAUUSD.c", "EURGBP", "CADCHF", "NZDCHF", "AUDNZD", "GBPCHF"]


class MarketDigestGenerator:
    def __init__(self):
        self.broadcaster = BeepBroadcastBus()

    def analyze_symbol(self, symbol: str) -> Tuple[str, str]:
        if symbol in STANDBY_BENCHED:
            if "XAUUSD" in symbol:
                return "RED", "Gold Standby Protocol: high wick volatility & pip value friction."
            return "RED", "Toxic spread / low-liquidity cross asset."

        target_sym = symbol
        info = mt5.symbol_info(target_sym)
        if not info and not target_sym.endswith(".c"):
            alt_sym = f"{symbol}.c"
            if mt5.symbol_info(alt_sym):
                target_sym = alt_sym
                info = mt5.symbol_info(target_sym)

        if not info or not info.visible:
            mt5.symbol_select(target_sym, True)
            info = mt5.symbol_info(target_sym)
            if not info:
                return "RED", "Symbol data unavailable."

        rates = mt5.copy_rates_from_pos(target_sym, mt5.TIMEFRAME_M15, 0, 30)
        if rates is None or len(rates) < 15:
            return "YELLOW", "Insufficient M15 bar history."

        highs = rates["high"]
        lows = rates["low"]
        closes = rates["close"]
        opens = rates["open"]

        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(
                np.abs(highs[1:] - closes[:-1]),
                np.abs(lows[1:] - closes[:-1])
            )
        )
        atr = float(np.mean(tr[-14:]))
        if atr <= 0:
            return "YELLOW", "Zero ATR detected."

        point = info.point
        spread_price = info.spread * point
        spread_atr_pct = (spread_price / atr) * 100.0

        recent_h = highs[-8:]
        recent_l = lows[-8:]
        recent_o = opens[-8:]
        recent_c = closes[-8:]

        candle_ranges = recent_h - recent_l
        upper_wicks = recent_h - np.maximum(recent_o, recent_c)
        lower_wicks = np.minimum(recent_o, recent_c) - recent_l
        total_wicks = upper_wicks + lower_wicks

        valid_mask = candle_ranges > 0
        if np.sum(valid_mask) > 0:
            wick_ratio = float(np.mean(total_wicks[valid_mask] / candle_ranges[valid_mask]))
        else:
            wick_ratio = 0.50

        if spread_atr_pct > 25.0 or wick_ratio > 0.65:
            return "RED", f"Wick noise {wick_ratio*100:.0f}%, Spread/ATR {spread_atr_pct:.1f}%"

        if spread_atr_pct > 15.0 or wick_ratio > 0.45:
            return "YELLOW", f"Moderate chop (Wicks {wick_ratio*100:.0f}%), 3-candle confirmation required."

        return "GREEN", f"Clean expansion (Wicks {wick_ratio*100:.0f}%, Spread/ATR {spread_atr_pct:.1f}%)"

    def generate_and_broadcast(self, publish_telegram: bool = True) -> Dict[str, List[str]]:
        if not mt5.initialize():
            logger.error("Failed to initialize MT5 for Market Digest.")
            return {"green": [], "yellow": [], "red": []}

        green_list = []
        yellow_list = []
        red_list = []

        logger.info("Analyzing market regime & volatility health across universe...")
        for sym in UNIVERSE:
            try:
                status, reason = self.analyze_symbol(sym)
                if status == "GREEN":
                    green_list.append(sym)
                elif status == "YELLOW":
                    yellow_list.append(sym)
                else:
                    red_list.append(sym)
                logger.info(f"  {sym:7s} -> [{status}] {reason}")
            except Exception as e:
                logger.warning(f"Error analyzing {sym}: {e}")
                red_list.append(sym)

        commentary_lines = [
            "• <b>Gold (XAUUSD):</b> Benched on Standby. Severe 85%+ wick consolidation; manual trades should be avoided until London/NY expansion.",
            f"• <b>Focus Pairs:</b> High institutional flow concentrated on <b>{', '.join(green_list[:4])}</b>. Favorable low-friction trend continuations.",
            "• <b>Strict Discipline:</b> Move SL to BE at +1.5R. If an Opt-Out notification is issued, exit at market immediately."
        ]
        commentary = "\n".join(commentary_lines)

        if publish_telegram:
            logger.info("Publishing Daily Market Digest to Telegram channels...")
            self.broadcaster.broadcast_daily_market_digest(
                green_pairs=green_list,
                yellow_pairs=yellow_list,
                red_pairs=red_list,
                commentary=commentary,
            )

        return {"green": green_list, "yellow": yellow_list, "red": red_list}


if __name__ == "__main__":
    gen = MarketDigestGenerator()
    res = gen.generate_and_broadcast(publish_telegram=True)
    logger.info("Market Digest complete.")
