# 05 — Current State & Risks

This is what is actually happening on disk right now (2026-09-16), independent of what the design
documents claim.

## Runtime state

- `overnight_status.json` → `mode: "DRY_RUN"`, `account: 0`, `equity/balance/free_margin: 0.0`,
  no open positions, zero trades.
- `v2/coexistence_status.json` → default `balance/equity = 10000.0`, zero positions, breaker inactive.
- `edge_matrix_status.json` → a completed 204-front edge scan (last run 2026-09-09).
- `broadcast_stream.jsonl` (33 MB) → append-only signal/deal events, including synthetic-looking
  deal tickets (`999888777`, `999111`).
- `overnight_execution.log` (23 MB) → latest entries show whitelist hot-reloads, edge-filter skips,
  and a simulated `LOSS DETECTED` on `Deal #999111`.

**Interpretation:** nothing is trading real money right now. The system is in dry-run/simulated mode,
and the "deals" in its telemetry are not confirmed broker fills.

## Real vs. fabricated data

- The investor ledger (`vault/investor_reports/trade_ledger.csv`) contains **4 deals** with sequential
  tickets (1001–1004) and tidy R-multiples — consistent with the audit's finding that
  `investor_reporting.py` seeds hardcoded fake deals when no real ledger exists.
- The broadcast stream's win/loss events and the admin dashboard's "92.6% / 87.1%" win rates are
  hardcoded, not measured.

## Secrets on disk (flagged, values redacted)

These files hold real credentials in plaintext and are **not committed to git**, but they live on the
OneDrive-synced folder:

| File | Contains |
|---|---|
| `.env` | Supabase URL, anon key, **service-role key** + affiliate URL |
| `config/broker_config.json` | **Plaintext MT5 passwords** for 3 accounts (2 demo, 1 real cent) |
| `config/telegram_config.json` | **Telegram bot token** + channel IDs |
| `config/client_accounts.json` | MT5 account IDs, owner names, balances |
| `frontend/.env.local` | Next.js env vars |

The Fernet key that encrypts MT5 credentials (`core/credential_vault.py`) is derived from
`SUPABASE_SERVICE_ROLE_KEY` — so rotating the Supabase key would silently undecrypt all stored
passwords.

## Data coverage

- Historical data exists **only for XAUUSD** (`data/dukascopy/`, 5 years, D1→M1) — yet the system
  claims multi-pair coverage (EURJPY, GBPJPY, USDCAD, BTCUSD, NASDAQ, DJ30).
- `vault/flight_recorder/` (the sub-second post-trade telemetry store) is **empty**.

## The real risks, ranked

1. **False confidence.** The biggest operational risk is that a green dashboard ("CONNECTED",
   "verified", "92.6% WR") is believed while nothing is actually trading or measuring. This is a
   *human/decision* risk before it is a technical one.
2. **Broken risk limits.** The 50%-vs-5% breaker and the missing cTrader breaker path mean the
   "capital preservation" promise is not enforced where it matters.
3. **Credential exposure.** Plaintext broker and Telegram credentials on a cloud-synced folder,
   plus a fragile Fernet-key derivation.
4. **Unfinished migration.** The cTrader bridge is a stub; the only working execution is
   Windows/MT5-bound.
5. **Unverifiable edge.** No multi-pair historical data and fabricated backtest/report data mean
   the claimed "edge" cannot currently be independently verified.
