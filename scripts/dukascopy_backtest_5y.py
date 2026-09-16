"""
========================================================================================
     SAJIM QUANT LABS — DUKASCOPY 5-YEAR GRAND TRINITY BACKTEST ENGINE
========================================================================================
Runs the full Grand Trinity Backtest on all downloaded Dukascopy CSVs.
Completely offline — no MT5 terminal required.

Engines evaluated on 5 years of institutional Dukascopy Gold (XAUUSD) data:
  1. Mirage Liquidity Sweep Pro (CHoCH Confirmed) — Stand-alone
  2. Grand Trinity Unified: Mirage LSP + Trend Duration Lifecycle + BEEP Kinetic Mass

Timeframes: M1, M5, M15, H1, 2H, H4, D1, 1W, 1M
Modes:      per-year walk-forward + full 5-year aggregate
========================================================================================
"""

import sys, os, csv, time
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Ensure Windows console UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DATA_DIR = os.path.join(BASE_DIR, "data", "dukascopy")
REPORT_PATH = os.path.join(BASE_DIR, "docs", "DUKASCOPY_5Y_BACKTEST_REPORT.md")

from v2.engine.liquidity_sweep_engine import MirageLiquiditySweepEngine, LiquiditySweepSignal
from v2.trend_duration_engine import TrendDurationEngine
from scripts.evaluate_mirage_liquidity_sweep import MirageBacktestSimulator

# ─── Rate dtype compatible with existing engines ──────────────────────────────
RATE_DTYPE = np.dtype([
    ('time',        'i8'),
    ('open',        'f8'),
    ('high',        'f8'),
    ('low',         'f8'),
    ('close',       'f8'),
    ('tick_volume', 'i8'),
    ('spread',      'i4'),
    ('real_volume', 'i8'),
])

# ─── Timeframe metadata ────────────────────────────────────────────────────────
TF_CONFIGS = [
    # (label, csv_stem, min_bars_required)
    ("M1",  "xauusd_m1_5y.csv",   5000),
    ("M5",  "xauusd_m5_5y.csv",   3000),
    ("M15", "xauusd_m15_5y.csv",  1500),
    ("H1",  "xauusd_h1_5y.csv",   500),
    ("2H",  "xauusd_2h_5y.csv",   300),
    ("H4",  "xauusd_h4_5y.csv",   200),
    ("D1",  "xauusd_d1_5y.csv",   100),
    ("1W",  "xauusd_1w_5y.csv",   50),
    ("1M",  "xauusd_mn1_5y.csv",  12),
]

# Gold spread friction per timeframe (in price points)
SPREAD_MAP = {
    "M1":  0.25,   # Wide — London/NY overlap only in real life
    "M5":  0.22,
    "M15": 0.20,
    "H1":  0.18,
    "2H":  0.18,
    "H4":  0.18,
    "D1":  0.15,
    "1W":  0.15,
    "1M":  0.15,
}


def load_csv_to_rates(csv_path: str) -> Optional[np.ndarray]:
    """Load a Dukascopy CSV into a structured NumPy rates array."""
    if not os.path.exists(csv_path):
        print(f"  [!] File not found: {csv_path}", flush=True)
        return None

    rows = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                ts = int(time.mktime(
                    datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S").timetuple()
                ))
                spread_pts = 20
                rows.append((
                    ts,
                    float(r["open"]),
                    float(r["high"]),
                    float(r["low"]),
                    float(r["close"]),
                    max(1, int(float(r.get("volume", 1)) * 1000)),
                    spread_pts,
                    0,
                ))
            except Exception:
                continue

    if not rows:
        return None

    return np.array(rows, dtype=RATE_DTYPE)


def slice_by_year(rates: np.ndarray, year: int) -> np.ndarray:
    """Return only bars within a given calendar year."""
    start_ts = int(datetime(year, 1, 1).timestamp())
    end_ts   = int(datetime(year + 1, 1, 1).timestamp())
    mask = (rates['time'] >= start_ts) & (rates['time'] < end_ts)
    return rates[mask]


def compute_beep_kinetic_mass(closes: np.ndarray, window: int = 14) -> np.ndarray:
    """BEEP Kinetic Mass M(t) — sign autocorrelation measure."""
    n = len(closes)
    m_t = np.zeros(n, dtype=np.float64)
    if n < window + 2:
        return m_t
    diffs = np.diff(closes)
    signs = np.sign(diffs)
    for i in range(window, len(signs)):
        sub = signs[i - window: i]
        m_t[i + 1] = (np.sum(sub) / window) * 100.0
    return m_t


def compute_trend_dirs_and_maturity(
    rates: np.ndarray,
    hma_len: int = 50,
    trend_len: int = 3
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute HMA-based trend direction and maturity ratio arrays."""
    closes = rates['close']
    n = len(closes)
    hma = TrendDurationEngine.calculate_hma(closes, length=hma_len)
    trend_dirs = np.zeros(n, dtype=int)
    maturity_ratios = np.zeros(n, dtype=float)
    bull_mem, bear_mem = [], []
    cur_t, cur_c = 0, 0

    for i in range(hma_len + trend_len + 1, n):
        is_up = all(hma[i - k] > hma[i - k - 1] for k in range(trend_len))
        is_dn = all(hma[i - k] < hma[i - k - 1] for k in range(trend_len))
        prev = cur_t
        if is_up:
            cur_t = 1
        elif is_dn:
            cur_t = -1

        if cur_t != 0 and cur_t != prev:
            if prev == 1 and cur_c > 0:
                bull_mem.append(cur_c)
                if len(bull_mem) > 10: bull_mem.pop(0)
            elif prev == -1 and cur_c > 0:
                bear_mem.append(cur_c)
                if len(bear_mem) > 10: bear_mem.pop(0)
            cur_c = 1
        elif cur_t != 0:
            cur_c += 1

        trend_dirs[i] = cur_t
        if cur_t == 1:
            exp_l = np.mean(bull_mem) if bull_mem else 20.0
            maturity_ratios[i] = cur_c / exp_l
        elif cur_t == -1:
            exp_l = np.mean(bear_mem) if bear_mem else 20.0
            maturity_ratios[i] = cur_c / exp_l

    return trend_dirs, maturity_ratios


def run_backtest_on_rates(
    rates: np.ndarray,
    tf_label: str,
    mirage_engine: MirageLiquiditySweepEngine,
    mode: str = "trinity",   # "mirage" or "trinity"
) -> Dict[str, Any]:
    """Run a full backtest on a rates array. Returns stats dict."""
    n = len(rates)
    if n < 200:
        return {"trades": 0, "win_rate": 0.0, "net_r": 0.0, "profit_factor": 0.0,
                "expectancy": 0.0, "max_dd_r": 0.0, "wins": 0, "losses": 0, "be": 0}

    # 1. Get Mirage sweep signals
    signals, _ = mirage_engine.analyze(rates)
    if not signals:
        return {"trades": 0, "win_rate": 0.0, "net_r": 0.0, "profit_factor": 0.0,
                "expectancy": 0.0, "max_dd_r": 0.0, "wins": 0, "losses": 0, "be": 0}

    if mode == "trinity":
        # 2. Compute HMA trend dirs + maturity (skip on very short or very high-bar arrays for speed)
        hma_len = min(50, max(10, n // 100))
        trend_dirs, maturity_ratios = compute_trend_dirs_and_maturity(rates, hma_len=hma_len)

        # 3. Compute BEEP Kinetic Mass
        closes = rates['close']
        m_t_arr = compute_beep_kinetic_mass(closes, window=14)

        # 4. Filter to Trinity-approved signals
        filtered = []
        for sig in signals:
            idx = sig.bar_index
            if idx >= n:
                continue
            t_dir = trend_dirs[idx]
            mat = maturity_ratios[idx]
            m_t = m_t_arr[idx]
            is_buy = (sig.direction == "BUY")
            is_sell = (sig.direction == "SELL")
            if ((is_buy and t_dir == 1 and mat <= 0.85 and m_t >= 0.0) or
                    (is_sell and t_dir == -1 and mat <= 0.85 and m_t <= 0.0)):
                filtered.append(sig)
        signals = filtered

    if not signals:
        return {"trades": 0, "win_rate": 0.0, "net_r": 0.0, "profit_factor": 0.0,
                "expectancy": 0.0, "max_dd_r": 0.0, "wins": 0, "losses": 0, "be": 0}

    # 5. Simulate
    res = MirageBacktestSimulator.simulate(rates, signals)
    return res


def format_pf(pf: float) -> str:
    return f"{pf:.2f}" if pf < 90 else "INF"


def generate_report(all_results: List[Dict]) -> str:
    report = """# Sajim Quant Labs — Dukascopy 5-Year Grand Trinity Backtest Report
**Asset**: Gold vs US Dollar (XAUUSD)  
**Data Source**: Dukascopy Institutional Tick Feed (Bid Price)  
**Date Range**: Sept 2021 – Sept 2026 (~5 Years)  
**Engines**: Mirage Liquidity Sweep Pro + Trend Duration Lifecycle + BEEP Kinetic Mass  

---

## Executive Summary

"""
    # Aggregate Trinity across all TFs
    trinity_rows = [r for r in all_results if r["mode"] == "trinity" and r["trades"] > 0]
    if trinity_rows:
        tot_trades = sum(r["trades"] for r in trinity_rows)
        tot_wins = sum(r["wins"] for r in trinity_rows)
        tot_r = sum(r["net_r"] for r in trinity_rows)
        macro_wr = (tot_wins / tot_trades * 100) if tot_trades > 0 else 0
        macro_exp = (tot_r / tot_trades) if tot_trades > 0 else 0
        gross_win = sum(r["net_r"] for r in trinity_rows if r["net_r"] > 0)
        gross_loss = abs(sum(r["net_r"] for r in trinity_rows if r["net_r"] < 0))
        macro_pf = (gross_win / gross_loss) if gross_loss > 0 else 99.0

        report += f"""> [!IMPORTANT]
> **GRAND TRINITY — 5-YEAR AGGREGATE PERFORMANCE**
> - **Total Trades Taken**: {tot_trades:,}
> - **Macro Win Rate**: **{macro_wr:.1f}%**
> - **Cumulative Net Yield**: **{tot_r:+.1f} R-multiples**
> - **Mathematical Expectancy**: **{macro_exp:+.3f} R per trade**
> - **Portfolio Profit Factor**: **{format_pf(macro_pf)}**

"""

    # Per-timeframe table — Mirage vs Trinity
    report += """---

## Per-Timeframe Results: Mirage LSP vs Grand Trinity

| TF | Mode | Period | Trades | Win Rate % | Net R | Profit Factor | Expectancy | Max DD |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for r in all_results:
        if r["trades"] == 0:
            row = f"| **{r['tf']}** | {r['mode'].upper()} | {r['period']} | — | — | — | — | — | — |\n"
        else:
            wr_icon = "🟢" if r["win_rate"] >= 55 else ("🟡" if r["win_rate"] >= 45 else "🔴")
            pf_str = format_pf(r["profit_factor"])
            row = (
                f"| **{r['tf']}** | {r['mode'].upper()} | {r['period']} "
                f"| {r['trades']} "
                f"| {wr_icon} **{r['win_rate']:.1f}%** "
                f"| **{r['net_r']:+.1f}R** "
                f"| {pf_str} "
                f"| **{r['expectancy']:+.3f}R** "
                f"| {r['max_dd_r']:.1f}R |\n"
            )
        report += row

    # Year-by-year breakdown for Trinity H1
    h1_years = [r for r in all_results if r["mode"] == "trinity" and r["tf"] == "H1" and r["period"] != "2021-2026"]
    if h1_years:
        report += """
---

## Walk-Forward Year-by-Year Breakdown (Grand Trinity, H1)

| Year | Trades | Win Rate % | Net R | Profit Factor | Expectancy |
| :--- | :---: | :---: | :---: | :---: | :---: |
"""
        for r in h1_years:
            if r["trades"] > 0:
                report += (
                    f"| **{r['period']}** | {r['trades']} | **{r['win_rate']:.1f}%** "
                    f"| **{r['net_r']:+.1f}R** | {format_pf(r['profit_factor'])} "
                    f"| **{r['expectancy']:+.3f}R** |\n"
                )

    report += """
---

## Verdict

"""
    if trinity_rows and macro_wr >= 55 and macro_pf >= 1.5:
        report += "> [!TIP]\n> **CERTIFIED FOR LIVE DEPLOYMENT**: Grand Trinity demonstrates consistent institutional edge across the full 5-year Dukascopy dataset.\n"
    elif trinity_rows and macro_wr >= 50:
        report += "> [!NOTE]\n> **BORDERLINE EDGE**: Grand Trinity passes minimum threshold. Consider tightening session filters before live deployment.\n"
    else:
        report += "> [!WARNING]\n> **EDGE NOT CONFIRMED**: Results do not meet the minimum Profit Factor >= 1.5 and Win Rate >= 55% threshold across all timeframes.\n"

    return report


def main():
    print("=" * 75, flush=True)
    print(" SAJIM QUANT LABS — DUKASCOPY 5-YEAR GRAND TRINITY BACKTEST", flush=True)
    print("=" * 75, flush=True)
    print(f" Data Directory : {DATA_DIR}", flush=True)
    print(f" Report Target  : {REPORT_PATH}", flush=True)
    print("=" * 75, flush=True)

    mirage_engine = MirageLiquiditySweepEngine(
        swing_len=21,
        lookback_bars=80,
        min_score=50.0,
        require_confirm=True,
        minor_len=8,
        confirm_window=13,
        sl_buffer=0.25,
        tp1_mult=1.0,
        tp2_mult=2.0,
        tp3_mult=3.0,
    )

    all_results = []
    years = list(range(2021, 2027))  # 2021 through 2026

    for tf_label, csv_stem, min_bars in TF_CONFIGS:
        csv_path = os.path.join(DATA_DIR, csv_stem)
        print(f"\n[>] Loading {tf_label}: {csv_stem}...", flush=True)

        rates_full = load_csv_to_rates(csv_path)
        if rates_full is None or len(rates_full) < min_bars:
            print(f"  [!] Skipping {tf_label} — insufficient data ({len(rates_full) if rates_full is not None else 0} bars < {min_bars})", flush=True)
            continue

        print(f"  Loaded {len(rates_full):,} bars. Running backtests...", flush=True)

        for mode in ["mirage", "trinity"]:
            # --- Full 5-year aggregate ---
            t0 = time.time()
            res = run_backtest_on_rates(rates_full, tf_label, mirage_engine, mode=mode)
            elapsed = time.time() - t0

            all_results.append({
                "tf": tf_label,
                "mode": mode,
                "period": "2021-2026",
                **res,
            })

            status = f"[{mode.upper():6}] 5Y Full: trades={res['trades']:>4} | WR={res['win_rate']:.1f}% | Net={res['net_r']:+.1f}R | PF={format_pf(res['profit_factor'])} | E={res['expectancy']:+.3f}R | {elapsed:.1f}s"
            print(f"  {status}", flush=True)

            # --- Walk-forward per year (only for Trinity to keep output manageable) ---
            if mode == "trinity":
                for year in years:
                    yr_rates = slice_by_year(rates_full, year)
                    if len(yr_rates) < max(30, min_bars // 20):
                        continue
                    yr_res = run_backtest_on_rates(yr_rates, tf_label, mirage_engine, mode=mode)
                    all_results.append({
                        "tf": tf_label,
                        "mode": mode,
                        "period": str(year),
                        **yr_res,
                    })
                    if yr_res["trades"] > 0:
                        print(f"    {year}: trades={yr_res['trades']:>3} | WR={yr_res['win_rate']:.1f}% | Net={yr_res['net_r']:+.1f}R | E={yr_res['expectancy']:+.3f}R", flush=True)

    # Generate and save report
    print("\n" + "=" * 75, flush=True)
    print(" GENERATING REPORT...", flush=True)
    print("=" * 75, flush=True)

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    report_md = generate_report(all_results)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\n[OK] Report saved: {REPORT_PATH}", flush=True)
    print("\n--- PREVIEW ---", flush=True)
    print(report_md[:3000], flush=True)
    print("=" * 75, flush=True)


if __name__ == "__main__":
    main()
