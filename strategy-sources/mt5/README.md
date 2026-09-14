# MQL5 strategy sources

The supplied `EMA_Pullback_TrendDuration_EA.mq5` is an MT5 Expert Advisor derived from the EMA pullback and trend-duration strategy, with an optional RSI divergence filter and alerts.

It is registered as an `mt5` Backtest Lab package. The web application can validate and queue the package, but it cannot execute MetaTrader Strategy Tester jobs on the Linux/web process. Actual testing requires the `.mq5` source, MT5 terminal, broker symbol history, and a Windows worker.

The EA must be tested with:

- Exact symbol and timeframe
- Broker-specific spread and commission
- Slippage assumptions
- H4 closed-bar EMA data
- Pivot confirmation lag
- Execution model and timezone
- Out-of-sample dates
- Every optional filter both enabled and disabled

No performance result is recorded until the Windows Strategy Tester worker produces a run artifact.