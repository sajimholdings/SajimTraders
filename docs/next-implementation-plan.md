# SajimOps Next Implementation Plan

## Current checkpoint

### Milestone completed: persistence-ready signal foundation

- Server-side Supabase REST adapter added in `src/lib/signal-store.ts`.
- Local fallback remains available only when Supabase configuration is absent.
- Vitest added with 7 passing tests across validation and store lifecycle.
- TypeScript validation and production build pass.
- New-turn report saved at `docs/new-turn-of-events-report.md`.

The next gate is connecting a staging Supabase project and proving authenticated persistence. Do not begin evidence storage or subscriber delivery until that gate passes.

### Milestone completed: Pine strategy evidence registration

- Preserved the supplied Pine source at `strategy-sources/pine/EMA_Pullback_with_TrendDuration.pine`.
- Registered `ema-pullback-trend-duration-v1` as a `PineScript` strategy source.
- Captured its entry rules, risk controls, parameters, and limitations without attaching unsupported performance claims.
- Added source-marker validation and a test that reads the checked-in Pine artifact.
- Test suite now passes 11 tests across signal validation, local persistence lifecycle, and Pine evidence registration.

The strategy remains `UNTESTED`. The next strategy gate is a reproducible backtest/forward-test evidence record with realistic spread, commission, slippage, symbol, timeframe, session, regime, drawdown, expectancy, and out-of-sample results.

### Milestone completed: Backtest Lab job boundary

- Added controlled strategy manifest validation for Pine and Python runtimes.
- Added required dataset, execution model, spread, commission, slippage, and deterministic seed fields.
- Added `GET/POST /api/backtests` and `GET /api/backtests/[runId]`.
- Added queued job records with explicit `execution: queued-only` response semantics.
- Added Backtest Lab documentation at `docs/backtest-lab.md`.
- Added four Backtest Lab contract tests; total suite is now 15 passing tests.
- Live API smoke test created and fetched a `QUEUED` Pine job successfully.

The next gate is an isolated worker design and a deterministic local adapter. No uploaded strategy code executes in the web process.

### MQL5 EA registration update

- Added `mt5` as a controlled Backtest Lab runtime.
- Registered `ema-pullback-trend-duration-ea` with the supplied risk, HMA, RSI, pivot, Friday-close, and trade-cap parameters.
- Added MQL5 source-structure validation tests.
- Actual Strategy Tester execution remains blocked until the `.mq5` source is available to the Windows worker and broker history/cost assumptions are specified.

The first functional slice is complete:

- Next.js 14 application bootstrapped.
- Signal submission validation exists for source, direction, prices, R:R, rationale, and expiry.
- `GET/POST /api/signals` and signal transition API exist.
- Local smoke testing proves invalid submissions return `400`, valid submissions enter `SUBMITTED`, and transitions work.
- Supabase migration exists for internal profiles, signal submissions, signal reviews, roles, and initial RLS.
- The current store uses an in-memory fallback when Supabase server credentials are absent. This is for local development only.

## Next objective

Move the signal workflow from prototype storage to authenticated, persistent, auditable operations without adding autonomous trading or investor functionality.

## Step 1: Persistent Supabase integration

1. Create a staging Supabase project or isolated staging schema.
2. Apply `supabase/migrations/0001_ops_signal_foundation.sql`.
3. Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` only to server environments.
4. Add a browser-safe public Supabase URL/key only when the auth client is implemented; never expose the service-role key.
5. Replace the prototype `submittedBy` label with the authenticated `ops_profiles.id` UUID.
6. Add a repository-level migration runner or documented Supabase CLI command.
7. Add integration tests for insert, list, transition, and review history.

## Step 2: Authentication and role enforcement

1. Add Supabase server client and secure session cookies.
2. Add middleware for `/ops/*`.
3. Load the current `ops_profiles` row on the server.
4. Return `401` for unauthenticated users and `403` for users without the required role.
5. Require MFA enrollment/verification before operational access.
6. Remove any development identity from production routes.
7. Add tests for founder, dev, risk, compliance_ops, trader, and expired auditor behavior.

## Step 3: Immutable review workflow

1. Add a `signal_reviews` insert whenever a signal changes state.
2. Enforce allowed transitions server-side instead of accepting every status from the client.
3. Prevent direct `PUBLISHED` transitions from `SUBMITTED`.
4. Require reviewer identity from the authenticated session.
5. Require risk/dev/founder role for review and publishing.
6. Add optional two-person approval for exceptional signals.
7. Add immutable versions when entry, SL, TP, direction, source, or expiry changes.
8. Add expiry processing and a retract/cancel reason.

## Step 4: Screenshot and evidence pipeline

1. Add Supabase Storage bucket for private screenshots.
2. Store object path and metadata, not public credentials or unrestricted URLs.
3. Restrict evidence access by signal scope and role.
4. Add checksum, upload timestamp, uploader, and optional analysis-result JSON.
5. Treat image analysis as advisory; a reviewer remains responsible for verification.

## Step 5: Strategy evidence registry

1. Add a `strategy_sources` or `strategy_evidence` table.
2. Store source type, version, test period, sample size, in/out-of-sample labels, spread/slippage assumptions, commission, max drawdown, expectancy, PF, losing streak, and regime/session breakdown.
3. Link every signal to an evidence record where available.
4. Keep BEEP, Pine Script, EMA, price action, and Python results separate.
5. Do not publish unsupported win-rate claims.

## Step 6: Subscriber delivery boundary

1. Add a publication record separate from signal verification.
2. Add subscriber eligibility/risk-profile rules without storing balances in this first milestone.
3. Implement one delivery adapter first, preferably an internal dashboard or private staff channel.
4. Add WhatsApp/Telegram delivery only through an authenticated server adapter.
5. Record recipient group, payload version, delivery result, retry count, and retract event.
6. Make expiry and cancellation updates explicit.

## Step 7: Ops screens and team workflow

1. Add authenticated ops shell and role-aware navigation.
2. Add dashboard for queue counts, review latency, published signals, expired signals, and failed deliveries.
3. Add signal queue with filters by source, trader, state, symbol, and expiry.
4. Add review detail with screenshot/evidence, gates, audit history, and immutable payload.
5. Add trader limits, cooldowns, duplicate warnings, and violation history.
6. Add feed, handoff, incidents, alerts, bot registry, and audit screens after signal operations are stable.

## Step 8: Bot and BEEP adapters

1. Define a signed signal envelope with UUID, source, strategy version, gate breakdown, timestamps, and expiry.
2. Add service-authenticated ingestion endpoints for BEEP and later Pine/Python adapters.
3. Store raw source payload separately from normalized signal fields.
4. Add deduplication by source event ID and signal UUID.
5. Keep ingestion separate from MT5 execution. No automatic order placement in this phase.

## Step 9: Verification gates

A phase is complete only when:

- Data persists across server restarts.
- API responses are validated and typed.
- Every mutation has an authenticated actor.
- RLS blocks cross-role and cross-scope access.
- Review history cannot be silently edited.
- Expired or retracted signals cannot be published.
- Duplicate source events do not create duplicate signals.
- Subscriber delivery is replayable and auditable.
- `npm run lint`, `npx tsc --noEmit`, and `npm run build` pass.
- No API or public page imports MT5/BEEP or exposes investor/account functionality.

## Explicit non-goals for this phase

- Autonomous MT5 execution.
- Client account balances or balance-linked sizing.
- Deposits, withdrawals, allocation, copy trading, or investor onboarding.
- Rewriting or declaring an edge for BEEP, Pine Script, EMA, or Python strategies.
- Visual redesign beyond functional states and basic structural styling.
