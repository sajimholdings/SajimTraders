"""
========================================================================================
            SAJIM HOLDINGS — EXPECTANCY & QUANT EDGE TRACKER
                        (core/expectancy_tracker.py)
========================================================================================
Calculates the Expected Value (EV) of the V2 Dual Bot live from MT5 history.
Formula: (Average Win * Number of Wins) - (Average Loss * Number of Losses)
========================================================================================
"""

import logging
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger("ExpectancyTracker")

MAGIC_V2 = 888222

class QuantExpectancyTracker:
    def __init__(self, history_days: int = 7):
        self.history_days = history_days

    def calculate_current_edge(self) -> Dict[str, Any]:
        """
        Pulls MT5 deal history for the last X days and calculates the V2 system EV.
        """
        if not mt5.terminal_info():
            return {"error": "MT5 not initialized"}

        d_from = datetime.now() - timedelta(days=self.history_days)
        d_to = datetime.now() + timedelta(days=1)
        
        deals = mt5.history_deals_get(d_from, d_to)
        if deals is None:
            return {"error": "No deals found"}

        hits = 0
        misses = 0
        total_win_amount = 0.0
        total_loss_amount = 0.0

        for d in deals:
            # Only track our V2 bot exits
            if d.magic != MAGIC_V2:
                continue
            if d.entry not in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT):
                continue
            
            # Ignore tiny scratch/BE trades under $0.10 for pure hit/miss stats
            if d.profit > 0.10:
                hits += 1
                total_win_amount += d.profit
            elif d.profit < -0.10:
                misses += 1
                total_loss_amount += abs(d.profit)

        total_trades = hits + misses
        if total_trades == 0:
            return {"error": "No valid V2 trades in window"}

        win_rate = (hits / total_trades) * 100
        avg_win = total_win_amount / hits if hits > 0 else 0.0
        avg_loss = total_loss_amount / misses if misses > 0 else 0.0

        # The core Sajim Expectancy Formula
        # Net Expectancy = (Number of Hits * Avg Output) - (Number of Misses * Risk)
        net_ev = (hits * avg_win) - (misses * avg_loss)

        status = "EDGE CONFIRMED (Printing Money) 💸" if net_ev > 0 else "EDGE DECAY (Needs BEEP Tuning) ⚠️"

        return {
            "total_trades": total_trades,
            "hits": hits,
            "misses": misses,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "net_ev": net_ev,
            "status": status
        }
