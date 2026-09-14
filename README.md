# SajimOps

Internal signal operations foundation for Sajim Holdings.

This repository starts with the human-in-the-loop workflow: traders submit setups, the system validates them, authorized staff review them, and only verified signals can move toward publication. It does not execute MT5 orders and does not contain investor account, deposit, withdrawal, allocation, or copy-trading features.

## Current functional slice

- `GET /api/health` provides service health.
- `GET /api/signals` lists signal submissions.
- `POST /api/signals` validates and stores a signal submission.
- `POST /api/signals/[id]` moves a signal through the prototype review lifecycle.
- `supabase/migrations/0001_ops_signal_foundation.sql` defines the initial roles, signal tables, review table, and RLS foundation.
- `docs/human-in-the-loop-automation-report.md` explains the operating model.
- `docs/next-implementation-plan.md` is the next execution source of truth.

## Development

```powershell
npm install
npm run dev
```

The current local fallback keeps signals in memory when `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are absent. This is only for development and smoke tests. Configure the server-only values from `.env.example` before staging.

```powershell
npx tsc --noEmit
npm run lint
npm run build
```

## Safety boundary

- The Supabase service-role key is server-only.
- The public/API process must not import MetaTrader 5 or BEEP.
- Review identity must come from authenticated Supabase sessions before staging.
- No unverified signal may be delivered to subscribers.
- Autonomous execution is deliberately deferred until evidence, permissions, idempotency, and bridge controls are implemented.

## Repository structure

```text
src/app/api/health/                 service health
src/app/api/signals/                signal intake and lifecycle API
src/lib/signal-domain.ts            validation and normalized signal contract
src/lib/signal-store.ts             Supabase adapter with development fallback
supabase/migrations/                database/RLS migrations
docs/                               operating report and implementation plan
```
