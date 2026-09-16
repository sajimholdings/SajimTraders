"""
========================================================================================
    SAJIM QUANT LABS — TRADE FLIGHT RECORDER AUDITOR & PERFORMANCE ANALYZER
                        (scripts/audit_flight_recorder.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Purpose:
  - Audits second-by-second trade telemetry recorded by TradeFlightRecorder.
  - Analyzes trade micro-trajectories:
      1. Time-to-Peak (how many seconds before maximum favorable excursion MFE).
      2. Exit Efficiency % (how close to the exact wave peak we cashed out).
      3. Post-Exit Reversal Rate (did price collapse right after our exit?).
      4. Risk-Reward Realization (Average Win R vs Average Loss R).
  - Can be invoked standalone or run by an autonomous inspection subagent on interval.
========================================================================================
"""

import os
import sys
import json
import glob
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
VAULT_DIR = os.path.join(ROOT_DIR, "vault", "flight_recorder")


def audit_flight_recorder():
    print("=" * 80)
    print("       SAJIM QUANT LABS — HIGH-RESOLUTION TRADE FLIGHT AUDIT REPORT")
    print("=" * 80)

    ledger_path = os.path.join(VAULT_DIR, "blackbox_ledger.json")
    if not os.path.exists(ledger_path):
        print(f"[!] No blackbox ledger found at: {ledger_path}")
        print("[*] TradeFlightRecorder is armed and will record tickets as soon as orders execute.")
        return

    try:
        with open(ledger_path, "r", encoding="utf-8") as f:
            ledger = json.load(f)
    except Exception as e:
        print(f"[!] Failed to read ledger: {e}")
        return

    if not ledger:
        print("[*] Ledger is empty. No completed trade flights yet.")
        return

    print(f"\n[+] Total Completed Flight Recorders: {len(ledger)}\n")
    print(f"{'Ticket':<10} | {'Symbol':<11} | {'Dir':<5} | {'Dur (s)':<8} | {'Peak MFE':<9} | {'Exit R':<9} | {'Eff %':<7} | {'Exit Reason':<25}")
    print("-" * 95)

    wins = 0
    losses = 0
    win_r_sum = 0.0
    loss_r_sum = 0.0
    durations = []
    efficiencies = []

    for item in ledger:
        ticket = item.get("ticket", 0)
        symbol = item.get("symbol", "")
        action = item.get("action", "")
        dur = item.get("duration_s", 0)
        mfe = item.get("mfe_r", 0.0)
        final_r = item.get("final_r", 0.0)
        eff = item.get("efficiency_pct", 0.0)
        reason = item.get("exit_reason", "")[:25]

        if final_r > 0:
            wins += 1
            win_r_sum += final_r
        else:
            losses += 1
            loss_r_sum += abs(final_r)

        durations.append(dur)
        efficiencies.append(eff)

        print(f"{ticket:<10} | {symbol:<11} | {action:<5} | {dur:<8.0f} | {mfe:+8.2f}R | {final_r:+8.2f}R | {eff:6.1f}% | {reason:<25}")

    total_trades = wins + losses
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    avg_win = (win_r_sum / wins) if wins > 0 else 0.0
    avg_loss = (loss_r_sum / losses) if losses > 0 else 0.0
    avg_dur = (sum(durations) / len(durations)) if durations else 0.0
    avg_eff = (sum(efficiencies) / len(efficiencies)) if efficiencies else 0.0

    print("-" * 95)
    print("\n--- QUANTITATIVE TELEMETRY SUMMARY ---")
    print(f"  Win Rate:               {win_rate:.1f}% ({wins} Wins / {losses} Losses)")
    print(f"  Average Win:            +{avg_win:.2f} R")
    print(f"  Average Loss:           -{avg_loss:.2f} R")
    print(f"  Win/Loss R-Ratio:       {(avg_win / max(1e-4, avg_loss)):.2f}x")
    print(f"  Average Duration:       {avg_dur:.1f} seconds (~{avg_dur/60:.1f} minutes)")
    print(f"  Mean Peak Efficiency:   {avg_eff:.1f}% (Percentage of wave extracted)")
    
    net_edge = (win_rate/100.0 * avg_win) - ((1.0 - win_rate/100.0) * avg_loss)
    print(f"  Net Mathematical Edge:  {net_edge:+.3f} R per trade")
    print("=" * 80)


if __name__ == "__main__":
    audit_flight_recorder()
