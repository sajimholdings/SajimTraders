"""
Dry run testing for EV Tracker
"""
import os
import sys
import json
import MetaTrader5 as mt5

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path.insert(0, ROOT_DIR)

from core.expectancy_tracker import QuantExpectancyTracker

def main():
    print("Testing EV Tracker...")
    # Load config to connect to live account
    cfg_path = os.path.join(ROOT_DIR, "config", "broker_config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r") as f:
            cfg = json.load(f)
        acc = cfg.get("active_account")
        pwd = cfg.get("password")
        srv = cfg.get("server")
        if acc and pwd and srv:
            mt5.initialize()
            mt5.login(acc, pwd, srv)
    else:
        mt5.initialize()

    tracker = QuantExpectancyTracker(history_days=7)
    stats = tracker.calculate_current_edge()
    
    print("\n[EV REPORT]")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    mt5.shutdown()

if __name__ == "__main__":
    main()
