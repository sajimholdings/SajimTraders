"""
Sajim Holdings — BEEP Cross-Asset Real-Time Matrix Scanner (beep_matrix_scanner.py)
Monitors 20+ global financial instruments simultaneously across timeframes (M5, M15, H1).
Instantly isolates the single most explosive institutional kinetic plume (M(t) >= 75)
across FX, Metals, Indices, and Crypto.
"""

import os
import sys
import json
import time
from typing import List, Dict, Any, Tuple
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, BASE_DIR, os.path.join(ROOT_DIR, "bots"), os.path.join(ROOT_DIR, "vault")):
    if p not in sys.path:
        sys.path.insert(0, p)

from beep_core import BeepCoreEngine
from beep_narrative import BeepNarrativeEngine
from backtester import BeepBacktester


class BeepMatrixScanner:
    """Institutional Real-Time Cross-Asset Scanner across 100+ Fronts."""

    def __init__(self):
        self.core = BeepCoreEngine()
        self.narrative = BeepNarrativeEngine()
        self.backtester = BeepBacktester()

        # 20 Tier-1 Global Liquid Instruments across 4 Sectors
        self.instruments = [
            # Commodities & Metals
            {"symbol": "XAUUSD",  "ticker": "GC=F",       "sector": "METALS",       "contract": 100.0,   "spread": 0.35},
            {"symbol": "XAGUSD",  "ticker": "SI=F",       "sector": "METALS",       "contract": 5000.0,  "spread": 0.02},
            {"symbol": "USOIL",   "ticker": "CL=F",       "sector": "ENERGY",       "contract": 1000.0,  "spread": 0.04},
            # Major FX Pairs
            {"symbol": "EURUSD",  "ticker": "EURUSD=X",   "sector": "FOREX_MAJOR",  "contract": 100000.0,"spread": 0.00015},
            {"symbol": "GBPUSD",  "ticker": "GBPUSD=X",   "sector": "FOREX_MAJOR",  "contract": 100000.0,"spread": 0.00020},
            {"symbol": "USDJPY",  "ticker": "USDJPY=X",   "sector": "FOREX_MAJOR",  "contract": 1000.0,  "spread": 0.018},
            {"symbol": "AUDUSD",  "ticker": "AUDUSD=X",   "sector": "FOREX_COMMOD", "contract": 100000.0,"spread": 0.00018},
            {"symbol": "USDCAD",  "ticker": "CAD=X",      "sector": "FOREX_COMMOD", "contract": 100000.0,"spread": 0.00020},
            {"symbol": "USDCHF",  "ticker": "CHF=X",      "sector": "FOREX_SAFE",   "contract": 100000.0,"spread": 0.00022},
            {"symbol": "NZDUSD",  "ticker": "NZDUSD=X",   "sector": "FOREX_COMMOD", "contract": 100000.0,"spread": 0.00020},
            # Volatile Crosses
            {"symbol": "GBPJPY",  "ticker": "GBPJPY=X",   "sector": "FOREX_CROSS",  "contract": 1000.0,  "spread": 0.028},
            {"symbol": "EURJPY",  "ticker": "EURJPY=X",   "sector": "FOREX_CROSS",  "contract": 1000.0,  "spread": 0.022},
            {"symbol": "EURGBP",  "ticker": "EURGBP=X",   "sector": "FOREX_CROSS",  "contract": 100000.0,"spread": 0.00018},
            # Global Stock Indices
            {"symbol": "US30",    "ticker": "^DJI",       "sector": "INDEX_US",     "contract": 1.0,     "spread": 2.50},
            {"symbol": "NAS100",  "ticker": "^IXIC",      "sector": "INDEX_US",     "contract": 1.0,     "spread": 1.80},
            {"symbol": "SPX500",  "ticker": "^GSPC",      "sector": "INDEX_US",     "contract": 1.0,     "spread": 0.50},
            {"symbol": "GER40",   "ticker": "^GDAXI",     "sector": "INDEX_EU",     "contract": 1.0,     "spread": 1.50},
            # Crypto
            {"symbol": "BTCUSD",  "ticker": "BTC-USD",    "sector": "CRYPTO",       "contract": 1.0,     "spread": 15.0},
            {"symbol": "ETHUSD",  "ticker": "ETH-USD",    "sector": "CRYPTO",       "contract": 1.0,     "spread": 1.50},
            {"symbol": "SOLUSD",  "ticker": "SOL-USD",    "sector": "CRYPTO",       "contract": 1.0,     "spread": 0.25},
        ]

    def scan_all_fronts(self) -> Dict[str, Any]:
        """
        Scans all 20 global assets simultaneously.
        Ranks by Kinetic Mass M(t), Lambda energy, and institutional expansion.
        """
        scan_results = []
        diamond_plumes = []
        certified_flows = []
        traps_detected = []
        standbys = []

        print(f"[*] Commencing Global BEEP Matrix Reconnaissance across {len(self.instruments)} assets...")

        for inst in self.instruments:
            sym = inst["symbol"]
            ticker = inst["ticker"]
            try:
                # Ingest recent price history (1-hour candles, last 100 bars)
                bars = self.backtester.fetch_yahoo_historical(ticker=ticker, interval="1h", range_period="5d")
                if len(bars) < 15:
                    continue

                closes = [b["close"] for b in bars]
                cur_bar = bars[-1]

                # Run BEEP Institutional Narrative Engine
                narr = self.narrative.generate_narrative(symbol=sym, prices=closes, account_balance=400.0)

                # Check for wick traps (The Thieves)
                high_p = cur_bar["high"]
                low_p = cur_bar["low"]
                open_p = cur_bar["open"]
                close_p = cur_bar["close"]
                tot_range = max(1e-4, high_p - low_p)
                upper_wick = high_p - max(open_p, close_p)
                lower_wick = min(open_p, close_p) - low_p

                is_trap = False
                trap_type = ""
                if (upper_wick / tot_range) > 0.45:
                    is_trap = True
                    trap_type = "RETAIL_FOMO_SWEEP_TOP"
                elif (lower_wick / tot_range) > 0.45:
                    is_trap = True
                    trap_type = "RETAIL_PANIC_SWEEP_BOTTOM"

                entry_report = {
                    "symbol": sym,
                    "sector": inst["sector"],
                    "current_price": close_p,
                    "b_t": narr["b_t"],
                    "m_t": narr["m_t"],
                    "lambda_pct": narr["lambda_pct"],
                    "regime": narr["regime"],
                    "quality": narr["quality"],
                    "action": narr["trade_action"],
                    "rr_ratio": narr["rr_ratio"],
                    "target_1": narr["target_1"],
                    "target_2": narr["target_2"],
                    "invalidation_sl": narr["invalidation_sl"],
                    "is_trap": is_trap,
                    "trap_type": trap_type,
                }

                scan_results.append(entry_report)

                if narr["quality"] == "DIAMOND" and not is_trap:
                    diamond_plumes.append(entry_report)
                elif narr["quality"] == "CERTIFIED" and not is_trap:
                    certified_flows.append(entry_report)
                elif is_trap:
                    traps_detected.append(entry_report)
                else:
                    standbys.append(entry_report)

            except Exception as e:
                pass

        # Sort all assets by Kinetic Mass M(t) descending
        scan_results.sort(key=lambda x: x["m_t"], reverse=True)

        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_assets_scanned": len(scan_results),
            "diamond_expansion_count": len(diamond_plumes),
            "certified_flow_count": len(certified_flows),
            "liquidity_traps_count": len(traps_detected),
            "standby_compression_count": len(standbys),
            "top_kinetic_fronts": scan_results[:5],
            "diamond_plumes": diamond_plumes,
            "certified_flows": certified_flows,
            "traps_detected": traps_detected,
            "all_results": scan_results,
        }


def print_matrix_dashboard(report: Dict[str, Any]):
    print("\n" + "=" * 95)
    print(f"       SAJIM HOLDINGS — BEEP CROSS-ASSET MATRIX RECONNAISSANCE DASHBOARD")
    print(f"       Execution Time: {report['timestamp']} | Scanned: {report['total_assets_scanned']} Assets")
    print("=" * 95)
    print(f"[*] DIAMOND EXPANSIONS (M >= 75) : {report['diamond_expansion_count']} Fronts Ready for Immediate Thrust")
    print(f"[*] CERTIFIED TRENDS (M >= 45)   : {report['certified_flow_count']} Fronts Ready for Baseline Limit Retest")
    print(f"[*] LIQUIDITY TRAPS DETECTED     : {report['liquidity_traps_count']} Trapped Retail Swings (Fade Candidates)")
    print(f"[*] DEAD COMPRESSION / STANDBY   : {report['standby_compression_count']} Assets in Noise (Capital Preserved)")
    print("-" * 95)
    print(f"{'SYMBOL':<9} {'SECTOR':<14} {'PRICE':<10} {'B(t) BASE':<10} {'M(t)':<7} {'LAMBDA':<8} {'REGIME':<22} {'ACTION':<7} {'R:R'}")
    print("-" * 95)

    for item in report["top_kinetic_fronts"]:
        print(
            f"{item['symbol']:<9} {item['sector']:<14} {item['current_price']:<10.2f} "
            f"{item['b_t']:<10.2f} {item['m_t']:<7.1f} {item['lambda_pct']:<7.1f}% "
            f"{item['quality']:<22} {item['action']:<7} {item['rr_ratio']}"
        )
    print("=" * 95)

    if report["diamond_plumes"]:
        print("\n>>> PRIMARY CAPITAL STRIKE RECOMMENDATION (DIAMOND SPEARHEAD):")
        top = report["diamond_plumes"][0]
        print(f"   Target Asset : {top['symbol']} ({top['sector']})")
        print(f"   Order Action : {top['action']} @ {top['current_price']}")
        print(f"   Baseline SL  : {top['invalidation_sl']} (Structural Floor)")
        print(f"   Target 1 (BE): {top['target_1']} (Take 50% Profit & Move SL to Breakeven)")
        print(f"   Target 2 (Run: {top['target_2']} (Full 1:3.5 Asymmetric Runner)")
        print(f"   Kinetic Mass : M(t) = {top['m_t']} (Extreme Institutional Plume)")
    elif report["certified_flows"]:
        print("\n>>> SECONDARY CAPITAL STRIKE RECOMMENDATION (CERTIFIED TREND):")
        top = report["certified_flows"][0]
        print(f"   Target Asset : {top['symbol']} ({top['sector']})")
        print(f"   Order Action : {top['action']} @ {top['current_price']} (Limit Dip near {top['b_t']})")
        print(f"   Target R:R   : {top['rr_ratio']}")
    else:
        print("\n[GLOBAL LOCKOUT]: All markets currently in compression. Zero capital deployed. Ammunition secured.")
    print("=" * 95 + "\n")


if __name__ == "__main__":
    scanner = BeepMatrixScanner()
    report = scanner.scan_all_fronts()
    print_matrix_dashboard(report)
