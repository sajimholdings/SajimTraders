"""
========================================================================================
            SAJIM HOLDINGS — INVESTOR REPORTING & TELEMETRY DECK
                            (core/investor_reporting.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Purpose:
  - Aggregates live cTrader deal ledger & open positions.
  - Computes investor-grade audit metrics via QuantEvaluator.
  - Optionally writes structured audit files (opt-in: export_files=True or
    INVESTOR_REPORT_EXPORT=1 — never on every API request by default):
      * vault/investor_reports/investor_audit_summary.json
      * vault/investor_reports/trade_ledger.csv
  - When there are no real deals, returns an explicit "no data" state (no demo deals).
  - Renders institutional executive cards for partners, bankers, and investors.
========================================================================================
"""

import os
import sys
import csv
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, BASE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

VAULT_REPORTS = os.path.join(ROOT_DIR, "vault", "investor_reports")

from core.ctrader_bridge import CTraderBridge
from core.quant_evaluator import QuantEvaluator

logger = logging.getLogger("InvestorReporting")
logging.basicConfig(level=logging.INFO)


class InvestorReporting:
    """
    Automated Quantitative Reporting Deck for Sajim Holdings Investors.
    """

    @classmethod
    def generate_investor_package(
        cls,
        bridge: Optional[CTraderBridge] = None,
        initial_capital: float = 10000.0,
        export_files: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Generates comprehensive investor performance report from cTrader ledger.

        Only real deals are evaluated. With no deals the package carries
        has_data=False and zeroed metrics. Files are written only when export_files
        is True (or INVESTOR_REPORT_EXPORT=1 when export_files is None).
        """
        if export_files is None:
            export_files = os.environ.get("INVESTOR_REPORT_EXPORT", "0") == "1"
        if bridge is None:
            bridge = CTraderBridge.get_instance()

        deals = bridge.get_deals(limit=500)
        telemetry = bridge.get_account_telemetry()

        deals = deals or []
        telemetry = telemetry or {}

        # Evaluate raw math
        eval_metrics = QuantEvaluator.evaluate_multi_bot_breakdown(deals, initial_capital=initial_capital)
        eval_metrics.setdefault("portfolio", {}).setdefault("investor_projections", {})

        package = {
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "fund_name": "SAJIM HOLDINGS QUANTITATIVE LABS",
            "founder": "Jimmy Mathu",
            "broker_backend": "cTrader Spotware Open API (Pure Python Cloud)",
            "account_telemetry": telemetry,
            "evaluation": eval_metrics,
            "raw_deals_count": len(deals),
            "has_data": bool(deals),
        }
        if not deals:
            package["message"] = "No closed trades recorded yet."

        if export_files:
            cls._export_files(package, deals)
        return package

    @classmethod
    def _export_files(cls, package: Dict[str, Any], deals: List[Dict[str, Any]]) -> None:
        os.makedirs(VAULT_REPORTS, exist_ok=True)

        # 1. Export JSON Summary
        summary_path = os.path.join(VAULT_REPORTS, "investor_audit_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(package, f, indent=2)

        # 2. Export CSV Ledger
        csv_path = os.path.join(VAULT_REPORTS, "trade_ledger.csv")
        fieldnames = ["ticket", "symbol", "action", "volume", "entry_price", "exit_price", "profit", "r_multiple", "label", "close_reason", "close_time"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for d in deals:
                writer.writerow(d)

        logger.info(f"[Investor Deck] Audit reports successfully exported to {VAULT_REPORTS}")

    @classmethod
    def render_executive_card(cls, package: Dict[str, Any]) -> str:
        """Renders an institutional investor-ready performance card."""
        if not package.get("has_data"):
            return "SAJIM HOLDINGS QUANTITATIVE LABS -- INVESTOR AUDIT REPORT\nNo closed trades recorded yet.\n"
        port = package["evaluation"]["portfolio"]
        bots = package["evaluation"]["bots"]
        telemetry = package["account_telemetry"]
        proj = port["investor_projections"]

        card = f"""
========================================================================================
             SAJIM HOLDINGS QUANTITATIVE LABS -- INVESTOR AUDIT REPORT
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Broker Infrastructure       : {package['broker_backend']}
Account ID & Environment    : {telemetry['account_id']} ({telemetry['environment']})
Audited Capital Base        : ${port['initial_capital']:,.2f} USD
Current Verified Equity     : ${port['current_equity']:,.2f} USD  (Net PnL: +${port['net_profit']:,.2f})
----------------------------------------------------------------------------------------
[+] RAW MATHEMATICAL EDGE VERIFICATION:
  - Mathematical Expectancy (EV) : +${port['expectancy_dollar']:.2f} / trade (+{port['expectancy_r']:.2f}R)
  - Profit Factor (PF)          : {port['profit_factor']:.2f} (Institutional Target: >= 1.40)
  - Win Rate / Loss Rate        : {port['win_rate_pct']:.1f}% Win | {port['loss_rate_pct']:.1f}% Loss
  - Payoff Asymmetry Ratio      : {port['payoff_ratio']:.2f} : 1 (Avg Win: ${port['avg_win']:.2f} | Avg Loss: ${port['avg_loss']:.2f})
  - Maximum Drawdown (MDD)      : {port['max_drawdown_pct']:.2f}% (${port['max_drawdown_dollars']:.2f})
  - Sharpe / Sortino Ratio      : {port['sharpe_per_trade']:.2f} / {port['sortino_per_trade']:.2f}
  - Recovery Factor             : {port['recovery_factor']:.2f}
  - Edge Sustainability Rating  : {port['sustainability']}

----------------------------------------------------------------------------------------
[+] INDIVIDUAL BOT ALPHA ATTRIBUTION:
  * Sajim V1 (Flagship)        : {bots['sajim_v1']['total_trades']} Trades | Win Rate: {bots['sajim_v1']['win_rate_pct']:.1f}% | Net PnL: +${bots['sajim_v1']['net_profit']:.2f} | PF: {bots['sajim_v1']['profit_factor']:.2f}
  * Sajim V2 (Young Surge)     : {bots['sajim_v2_surge']['total_trades']} Trades | Win Rate: {bots['sajim_v2_surge']['win_rate_pct']:.1f}% | Net PnL: +${bots['sajim_v2_surge']['net_profit']:.2f} | PF: {bots['sajim_v2_surge']['profit_factor']:.2f}
  * Sajim V2 (Mean Reversion)  : {bots['sajim_v2_revert']['total_trades']} Trades | Win Rate: {bots['sajim_v2_revert']['win_rate_pct']:.1f}% | Net PnL: +${bots['sajim_v2_revert']['net_profit']:.2f} | PF: {bots['sajim_v2_revert']['profit_factor']:.2f}

----------------------------------------------------------------------------------------
[+] INVESTOR CAPITAL SCALING PROJECTIONS (Compounded Growth Model):
  - 30-Day Projected Equity    : ${proj['projected_equity_30d']:,.2f} USD
  - 90-Day Projected Equity    : ${proj['projected_equity_90d']:,.2f} USD
  - 180-Day Projected Equity   : ${proj['projected_equity_180d']:,.2f} USD
  - 1-Year Projected Equity    : ${proj['projected_equity_365d']:,.2f} USD (+{proj['projected_1yr_roi_pct']:.1f}% ROI)
========================================================================================
Audit Summary Exported: vault/investor_reports/investor_audit_summary.json
Trade Ledger Exported : vault/investor_reports/trade_ledger.csv
========================================================================================
"""
        return card


if __name__ == "__main__":
    pkg = InvestorReporting.generate_investor_package(export_files=True)
    print(InvestorReporting.render_executive_card(pkg))
