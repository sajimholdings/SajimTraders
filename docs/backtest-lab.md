# Backtest Lab Foundation

The Backtest Lab accepts controlled strategy manifests and creates reproducible research jobs. The current milestone queues and tracks jobs only; it does not execute uploaded code.

Supported runtimes are `python`, `pine`, and `mt5`. MQL5 jobs are queued for a separate Windows Strategy Tester worker; they are never executed inside the Next.js or Linux API process.

## Required package shape

```json
{
  "strategyId": "ema-pullback",
  "displayName": "EMA Pullback",
  "version": "v1",
  "runtime": "pine",
  "entrypoint": "strategy.pine",
  "sourceFiles": ["strategy.pine"],
  "parameters": { "rrRatio": 2 },
  "datasetRequirements": {
    "symbols": ["XAUUSD"],
    "timeframes": ["M15"],
    "start": "2020-01-01",
    "end": "2024-01-01"
  }
}
```

## API

- `GET /api/backtests` lists queued research jobs.
- `POST /api/backtests` validates a manifest and creates a `QUEUED` job.
- `GET /api/backtests/:runId` returns a job status.

A job also requires explicit `datasetId`, `executionModel`, spread, commission, slippage, and deterministic seed. The response states `execution: queued-only` so this boundary cannot be mistaken for a live executor.

## Supplied MQL5 EA

The supplied `EMA_Pullback_TrendDuration_EA.mq5` is registered under:

```text
strategyId: ema-pullback-trend-duration-ea
runtime: mt5
version: 1.10-attached-source
chart timeframe: H1
higher-timeframe bias: H4
status: QUEUED_ONLY_UNTIL_WINDOWS_WORKER
```

The web/API milestone validates the package shape and queues a run. Actual MT5 Strategy Tester execution still requires the source file, MT5 terminal, broker history, symbol specifications, and a Windows worker.

## Worker milestone later

Execution will be added only through an isolated worker with no production credentials, no production database access, restricted dependencies/network, resource limits, cancellation, dataset checksums, and standardized result artifacts. Pine, Python, and MT5 require separate adapters; arbitrary uploads are rejected.
