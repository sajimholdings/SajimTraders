# 06 — Recommendations & Roadmap

Prioritized path to production readiness. Ordered by impact and dependency.

## Phase 0 — Before any live capital (non-negotiable)

1. **Stop fabricating success.**
   - Fix `core/api.py` (correct `mt5.ORDER_TYPE_BUY/SELL`, check `retcode == DONE`).
   - Remove the silent sandbox `return True` in `ctrader_bridge.connect()`.
   - Remove hardcoded PnL / win-rates / investor seeds.
   - Make `mt5_bridge` fail loudly instead of returning a fake price series.
2. **Fix the circuit breaker.**
   - Set `MAX_DAILY_DRAWDOWN_PCT` to `0.05` (5%).
   - Move breaker + high-watermark logic into `refresh_account_state()` so the cTrader path enforces it.
   - Normalize cTrader positions to `type`/`magic` (or make the shield read `label`).
3. **Rotate exposed credentials** (they have been sitting in plaintext on a synced folder):
   - Supabase service-role key, Telegram bot token, and the three MT5 passwords.
   - Re-derive the Fernet key independently of the Supabase key.

## Phase 1 — Make it run where you want it to run

4. **Make MT5 imports lazy/optional** across the ~20 sites and fix `v2/__init__.py` / `core/__init__.py`
   so strategy/API modules import cleanly on Linux.
5. **Fix the verified crashes** (mostly one-liners):
   - `order_type` NameError; `dealer_state_space` `delta_p`; `confluence_engine` inverted action;
     V1 `UnboundLocalError`; hummingbird/V2 short-feed `IndexError`; `bridge_supervisor` Logger call.
6. **Fix the sizing path** — replace `lot_calculator`'s $1/lot fallback with real point-value math,
   and stop the near-zero-stop → max-lot edge in the prop-firm bot.

## Phase 2 — Integrity & safety

7. **Web auth** — add `user_id` ownership checks to execute/close, require auth on investor/ctrader
   endpoints, add request models, fix CORS, use `hmac.compare_digest`.
8. **Repair or quarantine the prop-firm bot** — fix the import, `positions_get()` call, live branch,
   and drawdown baseline (measure from high-water mark).
9. **Bring tests green** — update stale assertions, inject BEEP keys into the test env, add fixtures
   for the edge-filter gate.

## Phase 3 — The real cTrader work (the actual product)

10. **Implement the cTrader Open API properly** (Protobuf auth → heartbeat → order/deal messages →
    reconnect), as a separate, scoped task. Until then, **rename the stub** so it cannot be mistaken
    for a live bridge (e.g. `ctrader_bridge_stub.py`).

## Phase 4 — Earn the claims

11. **Add real historical data** for the other claimed pairs (EURJPY, GBPJPY, USDCAD, BTCUSD, NASDAQ,
    DJ30) or shrink the claimed universe to what is actually covered (XAUUSD only).
12. **Validate BEEP empirically** against `data/dukascopy/` — measure actual win rate, PF, and
    expectancy rather than asserting 0.195% / 1.56% noise numbers. Make `investor_reporting.py`
    consume a real ledger only.

---

## A practical definition of "done"

The system is ready for even **demo live capital** only when:
- no code path reports success without a broker-confirmed result,
- the 5% daily breaker fires on **both** MT5 and cTrader paths,
- the bots import and run on the target (Linux/Render) environment,
- the test suite is green, and
- every "verified" number on the investor deck traces back to a real trade.
