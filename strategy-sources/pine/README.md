# Pine strategy sources

This directory stores versioned Pine Script inputs used for evidence tracking.

`EMA_Pullback_with_TrendDuration.pine` is registered as:

- Source: `PineScript`
- Version: `ema-pullback-trend-duration-v1`
- Evidence status: `UNTESTED`

The strategy currently describes H4 EMA bias, EMA20 pullback plus engulfing confirmation, swing-based stops, room-to-target trimming, optional HMA trend-duration alignment, daily trade cap, and Friday close behavior.

No performance claim is attached. Before promotion, run a reproducible backtest and forward test with realistic spread, commission, slippage, symbol, timeframe, session, and out-of-sample reporting.
