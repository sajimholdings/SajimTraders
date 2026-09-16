"""
========================================================================================
            SAJIM HOLDINGS — QUANTITATIVE EVALUATOR & RAW MATH ENGINE
                            (core/quant_evaluator.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Purpose:
  - Computes institutional quantitative metrics across individual bots and aggregate portfolio:
      * Mathematical Expectancy (EV in $ and R-multiple)
      * Profit Factor (PF) & Recovery Factor
      * Sharpe & Sortino Ratios (downside risk penalty)
      * Maximum Drawdown (MDD) & Peak Equity Trajectory
      * Win Rate, Payoff Ratio, and Asymmetry Index
      * Scaled Compounding Projections (30d, 90d, 180d, 365d) for Investors
========================================================================================
"""

import os
import sys
import math
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("QuantEvaluator")
logging.basicConfig(level=logging.INFO)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))


class QuantEvaluator:
    """
    Mathematical Edge and Sustainability Engine for Sajim Holdings.
    Audits live/historical trade executions for institutional validation.
    """

    @staticmethod
    def evaluate_trades(trades: List[Dict[str, Any]], initial_capital: float = 10000.0) -> Dict[str, Any]:
        """
        Takes a list of closed trade dictionaries and returns rigorous quant metrics.
        Each trade dict must contain:
          - 'profit': float ($ dollar PnL)
          - 'r_multiple': float (optional, payoff R)
          - 'label': str (bot identifier)
        """
        if not trades:
            return {
                "total_trades": 0,
                "status": "AWAITING_EXECUTIONS",
                "message": "No closed trades recorded yet.",
                "expectancy_dollar": 0.0,
                "profit_factor": 0.0,
                "win_rate_pct": 0.0,
                "initial_capital": initial_capital,
                "current_equity": initial_capital,
                "net_profit": 0.0,
                "max_drawdown_pct": 0.0,
                "sustainability": "PENDING_SAMPLE",
            }

        total_trades = len(trades)
        wins = [t for t in trades if t.get("profit", 0.0) > 0.05]
        losses = [t for t in trades if t.get("profit", 0.0) < -0.05]
        scratches = [t for t in trades if abs(t.get("profit", 0.0)) <= 0.05]

        num_wins = len(wins)
        num_losses = len(losses)
        num_scratches = len(scratches)

        win_rate = (num_wins / total_trades) * 100.0 if total_trades > 0 else 0.0
        loss_rate = (num_losses / total_trades) * 100.0 if total_trades > 0 else 0.0

        gross_profit = sum(t.get("profit", 0.0) for t in wins)
        gross_loss = abs(sum(t.get("profit", 0.0) for t in losses))
        net_profit = round(gross_profit - gross_loss, 2)

        avg_win = (gross_profit / num_wins) if num_wins > 0 else 0.0
        avg_loss = (gross_loss / num_losses) if num_losses > 0 else 0.0
        payoff_ratio = (avg_win / avg_loss) if avg_loss > 0 else avg_win

        # Profit Factor
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        # Mathematical Expectancy (EV)
        # E = (P(Win) * AvgWin) - (P(Loss) * AvgLoss)
        p_win = num_wins / total_trades
        p_loss = num_losses / total_trades
        expectancy_dollar = round((p_win * avg_win) - (p_loss * avg_loss), 2)

        # R-Multiple Expectancy
        r_vals = [t.get("r_multiple", 0.0) for t in trades]
        avg_r = sum(r_vals) / len(r_vals) if r_vals else 0.0

        # Equity Curve & Maximum Drawdown (MDD)
        peak = initial_capital
        current_eq = initial_capital
        max_dd_dollars = 0.0
        max_dd_pct = 0.0

        profits = [t.get("profit", 0.0) for t in trades]
        for p in profits:
            current_eq += p
            if current_eq > peak:
                peak = current_eq
            dd = peak - current_eq
            if dd > max_dd_dollars:
                max_dd_dollars = dd
            dd_pct = (dd / peak) * 100.0 if peak > 0 else 0.0
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        recovery_factor = round(net_profit / max_dd_dollars, 2) if max_dd_dollars > 0 else (99.0 if net_profit > 0 else 0.0)

        # Sharpe & Sortino (per-trade approximation)
        if len(profits) > 1:
            mean_ret = sum(profits) / len(profits)
            var_ret = sum((p - mean_ret) ** 2 for p in profits) / (len(profits) - 1)
            std_ret = math.sqrt(var_ret) if var_ret > 0 else 1.0
            sharpe_per_trade = round(mean_ret / std_ret, 3)

            downside_sq = [min(0, p) ** 2 for p in profits]
            downside_dev = math.sqrt(sum(downside_sq) / len(downside_sq)) if sum(downside_sq) > 0 else 1.0
            sortino_per_trade = round(mean_ret / downside_dev, 3)
        else:
            sharpe_per_trade = 0.0
            sortino_per_trade = 0.0

        # Sustainability & Company Scaling Verdict
        if expectancy_dollar > 0 and profit_factor >= 1.35 and max_dd_pct <= 5.0:
            sustainability = "INSTITUTIONAL ALPHA (HIGHLY SUSTAINABLE & INVESTOR-READY) [CONFIRMED_ALPHA]"
        elif expectancy_dollar > 0 and profit_factor >= 1.15:
            sustainability = "MODERATE EDGE (SUSTAINABLE WITH ASYMMETRIC MANAGEMENT) [MODERATE_EDGE]"
        elif expectancy_dollar > 0:
            sustainability = "MARGINAL EDGE (NEEDS HUMMINGBIRD TUNING) [TUNING_REQUIRED]"
        else:
            sustainability = "EDGE DECAY (REVISION REQUIRED) [HALT_EDGE_DECAY]"

        # Investor Scaling Projection (compounding model over N trades)
        # Assumes modest 10 trades per week at current EV
        trades_per_month = 40
        proj_30d = round(current_eq + (expectancy_dollar * trades_per_month), 2)
        proj_90d = round(current_eq + (expectancy_dollar * trades_per_month * 3 * 1.1), 2)
        proj_180d = round(current_eq + (expectancy_dollar * trades_per_month * 6 * 1.25), 2)
        proj_365d = round(current_eq + (expectancy_dollar * trades_per_month * 12 * 1.5), 2)

        return {
            "total_trades": total_trades,
            "wins": num_wins,
            "losses": num_losses,
            "scratches": num_scratches,
            "win_rate_pct": round(win_rate, 2),
            "loss_rate_pct": round(loss_rate, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "net_profit": net_profit,
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "payoff_ratio": round(payoff_ratio, 2),
            "expectancy_dollar": expectancy_dollar,
            "expectancy_r": round(avg_r, 2),
            "profit_factor": profit_factor,
            "max_drawdown_dollars": round(max_dd_dollars, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "recovery_factor": recovery_factor,
            "sharpe_per_trade": sharpe_per_trade,
            "sortino_per_trade": sortino_per_trade,
            "initial_capital": initial_capital,
            "current_equity": round(current_eq, 2),
            "sustainability": sustainability,
            "investor_projections": {
                "trades_modeled_per_month": trades_per_month,
                "projected_equity_30d": proj_30d,
                "projected_equity_90d": proj_90d,
                "projected_equity_180d": proj_180d,
                "projected_equity_365d": proj_365d,
                "projected_1yr_roi_pct": round(((proj_365d - initial_capital) / initial_capital) * 100, 2)
            }
        }

    @staticmethod
    def evaluate_multi_bot_breakdown(trades: List[Dict[str, Any]], initial_capital: float = 10000.0) -> Dict[str, Any]:
        """
        Segregates trades by bot label and evaluates performance for:
          - sajim_v1 (label="SAJIM_V1")
          - sajim_v2_surge (label="SAJIM_V2_SURGE")
          - sajim_v2_revert (label="SAJIM_V2_REVERT")
        """
        v1_trades = [t for t in trades if t.get("label") == "SAJIM_V1"]
        v2_surge_trades = [t for t in trades if t.get("label") == "SAJIM_V2_SURGE"]
        v2_revert_trades = [t for t in trades if t.get("label") == "SAJIM_V2_REVERT"]

        return {
            "portfolio": QuantEvaluator.evaluate_trades(trades, initial_capital=initial_capital),
            "bots": {
                "sajim_v1": QuantEvaluator.evaluate_trades(v1_trades, initial_capital=initial_capital / 3),
                "sajim_v2_surge": QuantEvaluator.evaluate_trades(v2_surge_trades, initial_capital=initial_capital / 3),
                "sajim_v2_revert": QuantEvaluator.evaluate_trades(v2_revert_trades, initial_capital=initial_capital / 3),
            }
        }


if __name__ == "__main__":
    # Test with synthetic test trades
    test_sample = [
        {"profit": 45.0, "r_multiple": 2.2, "label": "SAJIM_V2_SURGE"},
        {"profit": -18.0, "r_multiple": -1.0, "label": "SAJIM_V2_SURGE"},
        {"profit": 35.0, "r_multiple": 1.7, "label": "SAJIM_V1"},
        {"profit": 60.0, "r_multiple": 3.0, "label": "SAJIM_V2_SURGE"},
        {"profit": -15.0, "r_multiple": -1.0, "label": "SAJIM_V2_REVERT"},
        {"profit": 40.0, "r_multiple": 2.0, "label": "SAJIM_V2_REVERT"},
    ]
    report = QuantEvaluator.evaluate_multi_bot_breakdown(test_sample, initial_capital=10000.0)
    print(json.dumps(report, indent=2))
