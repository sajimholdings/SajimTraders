"""
========================================================================================
     SAJIM QUANT LABS — MULTI-WORKER DUKASCOPY INSTITUTIONAL DATA PIPELINE
========================================================================================
High-throughput parallel downloader for Dukascopy historical data.
Uses concurrent worker threads to download multi-year chunks simultaneously.

Supported Granularities:
- Native: MN1, D1, H4, H1, M30, M15, M5, M1
- Resampled: 1W (from D1), 2H (from H1)

Features:
- Multi-worker concurrent pool (default: 6 parallel workers)
- Resume & Skip existing completed chunks
- Automatic unbuffered logging
- Unified 5-year master CSV compilation
========================================================================================
"""

import os
import sys
import glob
import csv
import argparse
import subprocess
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Tuple

# Ensure Windows PowerShell/cmd cp1252 doesn't crash on print
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "data", "dukascopy")


def verify_environment():
    """Verifies that Node.js / npx is installed."""
    if shutil.which("npx") is None and shutil.which("npx.cmd") is None:
        print("[!] ERROR: 'npx' was not found in PATH.", flush=True)
        print("    Please ensure Node.js is installed.", flush=True)
        sys.exit(1)


def get_expected_chunk_filename(symbol: str, timeframe: str, start_date: str, end_date: str, price_type: str = "bid") -> str:
    return f"{symbol.lower()}-{timeframe.lower()}-{price_type.lower()}-{start_date}-{end_date}.csv"


def download_chunk_worker(args_tuple: Tuple) -> Tuple[str, str, str, str, bool, str]:
    """Worker task executed in parallel thread pool."""
    symbol, timeframe, start_date, end_date, output_dir, price_type, with_volume, skip_existing = args_tuple
    
    expected_filename = get_expected_chunk_filename(symbol, timeframe, start_date, end_date, price_type)
    expected_path = os.path.join(output_dir, expected_filename)
    
    if skip_existing and os.path.exists(expected_path) and os.path.getsize(expected_path) > 500:
        size_kb = os.path.getsize(expected_path) / 1024
        msg = f"[SKIP] Already exists: {expected_filename} ({size_kb:.1f} KB)"
        print(f"  {msg}", flush=True)
        return (symbol, timeframe, start_date, end_date, True, msg)

    cmd = [
        "npx", "--yes", "dukascopy-node",
        "-i", symbol.lower(),
        "-from", start_date,
        "-to", end_date,
        "-t", timeframe.lower(),
        "-f", "csv",
        "-p", price_type,
        "-df", "YYYY-MM-DD HH:mm:ss",
        "--directory", output_dir
    ]
    if with_volume:
        cmd.append("-v")

    t0 = time.time()
    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, shell=True)
    elapsed = time.time() - t0

    if result.returncode != 0:
        err_msg = (result.stderr or result.stdout).strip()
        print(f"  [!] Failed {symbol.upper()} [{timeframe.upper()}] {start_date} to {end_date}: {err_msg}", flush=True)
        return (symbol, timeframe, start_date, end_date, False, err_msg)
    else:
        size_str = ""
        if os.path.exists(expected_path):
            size_str = f"({os.path.getsize(expected_path) / 1024:.1f} KB)"
        msg = f"[OK] Downloaded {symbol.upper()} [{timeframe.upper()}] {start_date} to {end_date} {size_str} in {elapsed:.1f}s"
        print(f"  {msg}", flush=True)
        return (symbol, timeframe, start_date, end_date, True, msg)


def merge_chunks(symbol: str, timeframe: str, output_dir: str, master_filename: str) -> str:
    """Merges all year chunk CSVs for a timeframe into one unified sorted master CSV."""
    pattern = os.path.join(output_dir, f"{symbol.lower()}-{timeframe.lower()}-*.csv")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"[!] No chunk files found matching {pattern}", flush=True)
        return ""

    master_path = os.path.join(output_dir, master_filename)
    seen_timestamps = set()
    rows = []

    for fpath in files:
        if os.path.abspath(fpath) == os.path.abspath(master_path):
            continue
        try:
            with open(fpath, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    ts = r.get("timestamp")
                    if ts and ts not in seen_timestamps:
                        seen_timestamps.add(ts)
                        rows.append(r)
        except Exception as e:
            print(f"[!] Error reading chunk {fpath}: {e}", flush=True)

    # Sort chronologically
    rows.sort(key=lambda x: x["timestamp"])

    with open(master_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"  [OK] Master File created: {master_path} ({len(rows):,} total bars)", flush=True)
    return master_path


def resample_h1_to_2h(h1_csv_path: str, out_h2_path: str):
    """Resamples H1 master CSV into a 2H master CSV."""
    if not os.path.exists(h1_csv_path):
        print(f"[!] H1 file not found for 2H resampling: {h1_csv_path}", flush=True)
        return

    buckets: Dict[datetime, Dict[str, Any]] = {}
    with open(h1_csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                dt = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
                b_dt = datetime(dt.year, dt.month, dt.day, (dt.hour // 2) * 2, 0, 0)
                o = float(row["open"])
                h = float(row["high"])
                l = float(row["low"])
                c = float(row["close"])
                v = float(row.get("volume", 0))

                if b_dt not in buckets:
                    buckets[b_dt] = {"open": o, "high": h, "low": l, "close": c, "volume": v}
                else:
                    buckets[b_dt]["high"] = max(buckets[b_dt]["high"], h)
                    buckets[b_dt]["low"] = min(buckets[b_dt]["low"], l)
                    buckets[b_dt]["close"] = c
                    buckets[b_dt]["volume"] += v
            except Exception:
                continue

    sorted_keys = sorted(buckets.keys())
    with open(out_h2_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        for k in sorted_keys:
            b = buckets[k]
            writer.writerow({
                "timestamp": k.strftime("%Y-%m-%d %H:%M:%S"),
                "open": f"{b['open']:.3f}",
                "high": f"{b['high']:.3f}",
                "low": f"{b['low']:.3f}",
                "close": f"{b['close']:.3f}",
                "volume": f"{b['volume']:.4f}",
            })

    print(f"  [OK] 2H Resampled Master: {out_h2_path} ({len(sorted_keys):,} total bars)", flush=True)


def resample_d1_to_weekly(d1_csv_path: str, out_w1_path: str):
    """Resamples D1 master CSV into a 1W (Weekly) master CSV."""
    if not os.path.exists(d1_csv_path):
        print(f"[!] D1 file not found for Weekly resampling: {d1_csv_path}", flush=True)
        return

    buckets: Dict[date, Dict[str, Any]] = {}
    with open(d1_csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts_str = row["timestamp"]
                if " " in ts_str:
                    dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").date()
                else:
                    dt = datetime.strptime(ts_str, "%Y-%m-%d").date()

                monday = dt - timedelta(days=dt.weekday())
                o = float(row["open"])
                h = float(row["high"])
                l = float(row["low"])
                c = float(row["close"])
                v = float(row.get("volume", 0))

                if monday not in buckets:
                    buckets[monday] = {"open": o, "high": h, "low": l, "close": c, "volume": v}
                else:
                    buckets[monday]["high"] = max(buckets[monday]["high"], h)
                    buckets[monday]["low"] = min(buckets[monday]["low"], l)
                    buckets[monday]["close"] = c
                    buckets[monday]["volume"] += v
            except Exception:
                continue

    sorted_keys = sorted(buckets.keys())
    with open(out_w1_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        for k in sorted_keys:
            b = buckets[k]
            writer.writerow({
                "timestamp": f"{k.strftime('%Y-%m-%d')} 00:00:00",
                "open": f"{b['open']:.3f}",
                "high": f"{b['high']:.3f}",
                "low": f"{b['low']:.3f}",
                "close": f"{b['close']:.3f}",
                "volume": f"{b['volume']:.4f}",
            })

    print(f"  [OK] 1W (Weekly) Resampled Master: {out_w1_path} ({len(sorted_keys):,} total bars)", flush=True)


def generate_date_chunks(start_dt: date, end_dt: date) -> List[Tuple[str, str]]:
    """Splits a multi-year period into 1-year chunks."""
    chunks = []
    cur = start_dt
    while cur < end_dt:
        nxt = min(date(cur.year + 1, cur.month, cur.day), end_dt)
        chunks.append((cur.strftime("%Y-%m-%d"), nxt.strftime("%Y-%m-%d")))
        cur = nxt
    return chunks


def main():
    parser = argparse.ArgumentParser(description="Dukascopy 5-Year Parallel Historical Pipeline")
    parser.add_argument("--symbol", type=str, default="xauusd", help="Asset symbol (e.g. xauusd)")
    parser.add_argument("--years", type=int, default=5, help="Years of history (default: 5)")
    parser.add_argument("--from", dest="from_date", type=str, default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="to_date", type=str, default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR, help="Output folder")
    parser.add_argument("--price-type", type=str, default="bid", choices=["bid", "ask"], help="Bid or Ask price")
    parser.add_argument("--workers", type=int, default=6, help="Number of parallel worker threads (default: 6)")

    args = parser.parse_args()
    verify_environment()

    today = date.today()
    if args.to_date:
        end_dt = datetime.strptime(args.to_date, "%Y-%m-%d").date()
    else:
        end_dt = today

    if args.from_date:
        start_dt = datetime.strptime(args.from_date, "%Y-%m-%d").date()
    else:
        start_dt = end_dt - timedelta(days=args.years * 365)

    symbol = args.symbol.strip().lower()
    out_dir = os.path.abspath(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)

    date_chunks = generate_date_chunks(start_dt, end_dt)

    print("=" * 75, flush=True)
    print(f" SAJIM QUANT LABS — MULTI-WORKER DUKASCOPY PIPELINE ({args.workers} WORKERS)", flush=True)
    print("=" * 75, flush=True)
    print(f" Symbol         : {symbol.upper()} (Gold)", flush=True)
    print(f" Date Range     : {start_dt} to {end_dt} (~{args.years} Years)", flush=True)
    print(f" Yearly Chunks  : {len(date_chunks)} chunks per timeframe", flush=True)
    print(f" Granularities  : MN1, 1W, 1D, 4H, 2H, H1, M15, M5, M1", flush=True)
    print(f" Parallelism    : {args.workers} concurrent workers", flush=True)
    print(f" Target Folder  : {out_dir}", flush=True)
    print("=" * 75, flush=True)

    native_timeframes = ["mn1", "d1", "h4", "h1", "m15", "m5", "m1"]

    # Build queue of all tasks
    task_queue = []
    for tf in native_timeframes:
        for c_start, c_end in date_chunks:
            task_queue.append((
                symbol,
                tf,
                c_start,
                c_end,
                out_dir,
                args.price_type,
                True,  # with_volume
                True   # skip_existing
            ))

    print(f"\n[+] Total tasks in download matrix: {len(task_queue)} tasks across {len(native_timeframes)} timeframes", flush=True)
    print(f"[+] Starting concurrent worker pool with {args.workers} workers...\n", flush=True)

    t0_all = time.time()
    completed_count = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download_chunk_worker, t): t for t in task_queue}
        for future in as_completed(futures):
            sym, tf, s_dt, e_dt, success, msg = future.result()
            completed_count += 1

    total_time = time.time() - t0_all
    print(f"\n[+] All {completed_count} download tasks finished in {total_time:.1f}s!", flush=True)

    # Compile Master Files for all timeframes
    print("\n" + "=" * 75, flush=True)
    print(" COMPILING 5-YEAR UNIFIED MASTER FILES", flush=True)
    print("=" * 75, flush=True)

    for tf in native_timeframes:
        master_name = f"{symbol}_{tf}_5y.csv"
        merge_chunks(symbol, tf, out_dir, master_name)

    # Synthesize 1W and 2H
    print("\n[+] Synthesizing 1W (Weekly) and 2H Master Files...", flush=True)
    d1_master = os.path.join(out_dir, f"{symbol}_d1_5y.csv")
    w1_master = os.path.join(out_dir, f"{symbol}_1w_5y.csv")
    resample_d1_to_weekly(d1_master, w1_master)

    h1_master = os.path.join(out_dir, f"{symbol}_h1_5y.csv")
    h2_master = os.path.join(out_dir, f"{symbol}_2h_5y.csv")
    resample_h1_to_2h(h1_master, h2_master)

    print("\n" + "=" * 75, flush=True)
    print(" [OK] 5-YEAR MULTI-TIMEFRAME SUITE COMPLETED SUCCESSFULLY!", flush=True)
    print(f" Location: {out_dir}", flush=True)
    print("=" * 75, flush=True)


if __name__ == "__main__":
    main()
