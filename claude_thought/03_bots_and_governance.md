# 03 — Sajim Bots & Risk Governance

## The bot family

| Bot | File | Magic / label | Role |
|---|---|---|---|
| Sajim V1 | `bots/sajim_v1_bot.py` | `777999` | Flagship execution bot |
| Sajim V2 | `bots/sajim_v2_bot.py` | `888222` | Asymmetric production bot |
| Overnight server | `bots/sajim_server_overnight.py` | — | 24/7 dedicated daemon |
| Prop-firm challenge | `bots/prop_firm/prop_firm_challenge_bot.py` | — | FTMO/FundedNext challenge bot |

V2 runs two "cartridges":
- **Young Surge Continuation** — enters early trend life (maturity ≤ 0.60), targets 1:3.0 R:R.
- **Exhaustion Mean Reversion** — fades overextended trends (maturity ≥ 1.00, price ≥ 1.2×ATR from
  baseline), targets 1:2.0 R:R.

The **Dual Orchestrator** (`v2/dual_orchestrator.py`) runs V1 and V2 side-by-side on one account.

## Coexistence Gatekeeper (`v2/coexistence.py`)

The gatekeeper's job is to keep V1 and V2 from hurting each other on a shared account. Its
**docstring** lists six governance pillars, but the **actual constants in the code disagree** with
the docstring — this is a real, current bug (see the table):

| Governance rule | Docstring says | Code actually sets | Consequence |
|---|---|---|---|
| Max combined positions | 6 | `MAX_COMBINED_POSITIONS = 2` | Much tighter than documented |
| Min margin level | 500% | `MIN_MARGIN_LEVEL_PCT = 200.0` | Weaker protection |
| Max per-currency cluster | 2 | `MAX_CLUSTER_EXPOSURE = 1` | Tighter than documented |
| Daily drawdown breaker | **5.0%** | `MAX_DAILY_DRAWDOWN_PCT = 0.50` | **50%, not 5%** — 10× too loose |

The 5% vs 50% mismatch is the most serious: the headline risk-control promise is "halt at −5%
daily," but the code only halts at −50%.

### The six pillars as implemented

1. **Magic-number isolation** — V1 `777999` / V2 `888222`; each bot only manages its own positions.
2. **Aggregate cap** — blocks new entries once combined open positions reach `max_combined_positions`.
3. **Directional conflict shield** — refuses an opposing trade on the same symbol.
4. **Currency-cluster exposure cap** — limits positions per underlying currency.
5. **Daily drawdown circuit breaker** — halts entries if combined daily loss crosses the threshold.
6. **Telemetry** — writes `v2/coexistence_status.json` continuously.

### Where the gatekeeper is fragile

- **Two refresh paths, one enforced breaker.** The MT5 path `refresh()` *does* compute the circuit
  breaker and the protected-capital floor. The cTrader/cloud path `refresh_account_state()` **only
  updates balances and positions — it never evaluates the breaker.** So on cTrader the daily-loss
  circuit breaker silently does nothing.
- **Cross-broker schema mismatch.** The conflict shield reads `pos["type"]`, `pos["symbol"]`,
  `pos["magic"]`, `pos["ticket"]`. MT5 dicts have these; cTrader dicts use `label` instead → a
  `KeyError` as soon as ≥ 1 position is open on the cTrader path.
- **No thread safety.** V1 and V2 can signal concurrently, but there is no lock around the
  gatekeeper state; `save_status()` does a non-atomic remove-then-rename.

### Protected capital floor (high-watermark)

The MT5 path ratchets a protected-capital floor as equity grows (e.g. HWM ≥ $200 → floor $170;
≥ $150 → $125; …). If equity falls to the floor, the breaker engages. This is a reasonable
"banked profits" idea — but it only lives in the MT5 `refresh()`, not the cloud path.

## Prop-firm challenge bot (`bots/prop_firm/prop_firm_challenge_bot.py`)

- Account tiers $50k / $100k / $200k (FTMO, FundedNext, Headway).
- **Risk envelope:** 5.0% total drawdown (prop rule 8–10%), 3.5% daily (prop rule 5.0%),
  0.50% risk/trade, min 1:3.0 R:R, max 2 concurrent positions.
- **Current problems (from the audit):**
  - The module **cannot import** (`from sajim_omniverse_bot import UniversalLotCalculator` →
    `ModuleNotFoundError`).
  - The `--live` branch is a `print()` stub — no `order_send`.
  - Total drawdown is measured from **current balance**, not the challenge high-water mark, so
    after +10% profit it can lose ~15% before the breaker fires (breaching the 10% prop rule).
  - `mt5.positions_get(magic=...)` is not a valid MT5 API argument → `TypeError` every loop.

## Other risk controls

- **Sammy's 4-Check** (see `02_beep_framework.md`) — spread, kinetic mass, multi-scale alignment,
  and capital-preservation gates. (Note: in `beep_core.py` the 4-check is momentum / SL-vs-baseline /
  lot-size / lambda — a slightly different enumeration than the README's spread/kinetic/alignment/
  capital version; the *code* version is the one that actually runs.)
- **Trade-level risk:** SL/TP are attached, but (per the audit) there is **no validation** that
  `sl < entry < tp` and no spread/minimum-distance check.

---

### My notes on governance

The governance *design* — magic isolation, directional shield, cluster cap, daily breaker,
high-watermark floor — is genuinely sensible multi-bot hygiene. The problems are **execution
fidelity**: constants that contradict their own docstrings, a breaker that only works on the MT5
path, a schema assumption that breaks on cTrader, and a prop-firm bot that can't even import.
These are fixable, but they are exactly the kind of thing that silently misleads in production.
