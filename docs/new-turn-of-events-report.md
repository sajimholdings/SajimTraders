# SajimOps New Turn of Events Report

**Date:** 2026-09-14
**Milestone:** Signal persistence boundary and test-gated foundation
**Status:** Completed locally; Supabase staging connection is the next gate

## What changed

The project moved from a simple in-memory API prototype toward a persistence-ready internal operations service.

### 1. New repository foundation

A clean Next.js 14 repository now exists at:

```text
C:\Users\jimmy\OneDrive\Desktop\SAJIM Repo\sajim-ops
```

It is intentionally separate from the legacy `SajimTraders` client portal. The new repository is for the staff operations workflow and does not add investor accounts, deposits, withdrawals, allocation, copy trading, or autonomous execution.

### 2. Functional signal workflow

The application now supports:

```text
Submit -> Validate -> Review -> Verify -> Publish later
```

The first working endpoints are:

- `GET /api/health`
- `GET /api/signals`
- `POST /api/signals`
- `POST /api/signals/[id]`

The intake validates:

- Symbol and timeframe
- BUY/SELL price ordering
- Entry, stop loss, and take profit
- Minimum 1:2 R:R
- Supported source strategy
- Strategy version
- Rationale
- Future expiry timestamp

Supported source labels are:

- BEEP
- PineScript
- EMA
- Price action
- Python algorithm

### 3. Persistence boundary

`src/lib/signal-store.ts` now has a server-side Supabase REST adapter. When `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are configured, signal reads, inserts, and transitions target `signal_submissions` in Supabase.

When those values are absent, the app uses an in-memory fallback for local development and smoke tests only. This fallback is documented and must not be used as production storage.

The service-role key is never intended for browser code.

### 4. Database foundation

The initial migration defines:

- Internal roles
- `ops_profiles`
- `signal_submissions`
- `signal_reviews`
- Initial indexes
- Role helper functions
- Initial RLS policies

The database shape is prepared for authenticated staff workflows, but production writes still require the next authentication milestone so `submitted_by` comes from a real authenticated UUID rather than a development placeholder.

### 5. Test gate added

A Vitest test command now exists:

```powershell
npm test
```

Current milestone coverage:

- Valid BUY setup
- Valid SELL setup
- Invalid price ordering
- Insufficient R:R
- Unsupported source
- Expired signal
- Signal normalization
- Local store insert/list/transition lifecycle

Result:

```text
2 test files passed
7 tests passed
```

The project also passed TypeScript validation and the Next.js production build after dependency installation was repaired.

## Operational significance

This changes the current manual process in an important way. A trader's screenshot or strategy idea is now treated as a structured submission rather than an untracked WhatsApp message.

That creates the foundation for:

- Trader submission limits
- Reviewer accountability
- Source-by-source strategy comparison
- Expiry and retraction
- Subscriber delivery records
- Forward-test evidence
- Reduced overtrading
- Auditable shift handoffs

WhatsApp should eventually be a delivery adapter, not the source of truth.

## Issue encountered and resolved

The first test installation failed because the system disk had no free space (`ENOSPC`). Only generated artifacts were removed: the new repository's `node_modules`, generated `.next` output, npm cache, and temporary files. Source code, migrations, tests, and documentation were preserved.

Dependencies were then installed successfully and the test suite passed.

## What is not yet production-ready

- Supabase staging project has not yet been connected.
- Authenticated sessions and MFA are not implemented.
- Role checks are not yet wired into API routes.
- Review history is not yet inserted on every transition.
- Lifecycle transitions need a stricter server-side state machine.
- Screenshot storage and evidence records are not implemented.
- Subscriber delivery adapters are not implemented.
- BEEP/Pine/Python source ingestion adapters are not connected.
- MT5 execution remains deliberately out of scope for this milestone.

## Next milestone

The next milestone is **authenticated persistent signal operations**:

1. Apply the Supabase migration in staging.
2. Add server-side Supabase session handling.
3. Derive staff identity and role from `ops_profiles`.
4. Replace development submitter identity with authenticated UUIDs.
5. Enforce role and ownership checks on signal APIs.
6. Add immutable review records for transitions.
7. Add tests for authentication and every role boundary.
8. Re-run test, typecheck, build, and API smoke checks before starting evidence storage.

## Decision record

No new feature milestone should begin until the current milestone has an executable test gate. Visual polish remains deferred; data integrity, permissions, API behavior, and auditability remain the priority.
