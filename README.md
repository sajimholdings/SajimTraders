# SAJIM HOLDINGS — QUANTITATIVE LABS
### Trading bots, signal infrastructure and the Sajim Traders client portal
**Founder & Chief Quantitative Architect:** Jimmy Mathu

---

## Repository layout

```
bots/                     MT5 trading bots
  sajim_v1_bot.py           V1 flagship engine            (needs private BEEP modules)
  sajim_v2_bot.py           V2 edge-driven bot            (needs private BEEP modules)
  sajim_server_overnight.py Overnight daemon (V1 settings)
  prop_firm/                Prop-firm challenge bot       (needs private BEEP vault)
v2/                       V2 framework: strategies, coexistence gate, risk, execution
  safety.py                 Kill switch, cent-account helpers, daily drawdown guard
  execution/mt5_exec.py     Shared MT5 order helpers (dry-run gate, retries, filling fallback)
  risk/                     Ratchet / Hummingbird exits, thresholds, persisted position state
core/                     Shared engines: lot calculator, whitelist, Supabase bridge,
                          credential vault, cTrader bridge (stub), investor reporting
web/                      FastAPI backend (web/app.py, deployed on Render)
                          + legacy local stdlib gateway (web/server.py, localhost only)
frontend/                 Next.js client portal (deployed on Vercel, root dir = frontend)
scripts/                  MT5 bridge + supervisor, signal generator, research/backtest scripts
supabase/schema.sql       Database schema, RLS policies and idempotent migrations
config/                   master_trading_whitelist.json (single whitelist source)
tests/                    pytest suite + historical backtest artifacts (TEST_INDEX.md)
docs/                     Playbooks, reports, operations handbook
```

**Private modules.** `core/beep_*`, `core/tick_beep_engine.py` and `vault/` hold the
proprietary BEEP engines and are intentionally git-ignored. Commands and tests that need
them exit with a clear message (or are skipped) when they are absent.

---

## `run.py` commands

```bash
python run.py v1 [--live]            # V1 engine (dry run unless --live)
python run.py v2 [--live]            # V2 bot
python run.py dual [--live]          # V1 + V2 side by side (--broker mt5|ctrader)
python run.py server                 # Overnight daemon
python run.py propfirm --size 100000 # Prop-firm bot (--size is the drawdown baseline)
python run.py edge --oos-split 0.3   # Edge matrix backtest with out-of-sample check
python run.py backtest               # Backtester (--allow-synthetic to permit synthetic data)
python run.py web                    # Legacy local gateway (127.0.0.1)
python run.py api --port 8080        # BEEP gateway API
python run.py investor | digest | concierge | scanner | ctrader | test
```

Safety defaults:
- **Dry run by default.** Without `--live`, no order of any kind (entries, closes or
  SL/TP changes) is sent.
- **Kill switch.** Create a `KILL_SWITCH` file in the repo root, or set
  `SAJIM_KILL_SWITCH=1`, and every bot stops opening new trades. Open positions are
  still managed.
- **Conservative risk.**
  - Risk per trade is 1%; V2 adapts it up to a 2% maximum.
  - V1 and the overnight server hold at most 3 positions.
  - Daily drawdown is capped at 5% of start-of-day equity (UTC).
- **Cent accounts** (e.g. USC) are detected from the account currency, and USD floors
  are converted.
- **cTrader** order execution is **not implemented**. The bridge never reports fake
  fills; simulation must be requested explicitly (`--simulate` / `CTRADER_SIMULATION=1`).
- **Bot state files** are kept in `state/` (git-ignored; change it with `SAJIM_STATE_DIR`).

---

## Deployment

| Piece | Where | Notes |
|---|---|---|
| Backend `web/app.py` | Render (`render.yaml`) | Set `SUPABASE_*`, `ADMIN_KEY`, `CREDENTIAL_ENCRYPTION_KEY` |
| Client portal `frontend/` | Vercel | Root Directory = `frontend`; set `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` (see `frontend/.env.example`) |
| MT5 bridge + supervisor | Windows host | `pip install -r requirements.txt -r requirements-windows.txt`; one portable MT5 terminal per account (see `scripts/bridge_supervisor.py`) |
| Database | Supabase | Run `supabase/schema.sql` (idempotent) |

Copy `.env.example` to `.env` for local configuration. Never commit real credentials.

---

## Development

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests -q          # uses a safe MetaTrader5 stub on Linux

cd frontend && npm ci && npx tsc --noEmit && npm run lint && npm test && npm run build
```

CI (`.github/workflows/ci.yml`) runs both on every push to `main` and on every pull request.

---

## Risk governance: Sammy's 4-Check Gatekeeper

See `docs/SAMMYS_4_CHECK_RISK_POLICY.md`. Note: the V2 path applies its own spread,
coexistence and drawdown gates and does not run the full BEEP M(t)/Gamma checks.

Historical backtest results in `tests/TEST_INDEX.md` and `docs/` are research artifacts,
not live performance. `docs/edge_matrix_results.json` was produced by an earlier,
optimistic version of the edge-matrix backtest and should be regenerated before use.
