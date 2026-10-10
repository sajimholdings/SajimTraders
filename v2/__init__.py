"""
========================================================================================
                 SAJIM HOLDINGS QUANTITATIVE LABS — V2 ECOSYSTEM
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Modular Architecture:
  ├── v2.engine       : Vectorized Indicators, Statistical Trend Duration & Lifecycle Forecasting
  ├── v2.core         : Pluggable Strategy Contracts & Multi-Bot Coexistence Governance
  ├── v2.strategies   : Plug-and-Play Institutional Alpha Cartridges
  ├── v2.execution    : Production Bots & Dual-Concurrency Orchestrator
  ├── v2.risk         : Ratchets, Hummingbird harvest, persistent per-ticket risk state
  ├── v2.safety       : Kill switch, cent normalisation, UTC daily drawdown guard
  └── v2.api          : Real-time Telemetry, WebSocket Feeds & WebApp Bridge

Exports are resolved lazily: `import v2.coexistence`, `import v2.risk.ratchet`, ... do not
pull in MetaTrader5-dependent bots or the private BEEP modules.
========================================================================================
"""

import importlib

_LAZY_EXPORTS = {
    "TrendDurationEngine": ("v2.trend_duration_engine", "TrendDurationEngine"),
    "BaseStrategyCartridge": ("v2.strategy_base", "BaseStrategyCartridge"),
    "StrategySignal": ("v2.strategy_base", "StrategySignal"),
    "CoexistenceGatekeeper": ("v2.coexistence", "CoexistenceGatekeeper"),
    "MAGIC_V1": ("v2.coexistence", "MAGIC_V1"),
    "MAGIC_V2": ("v2.coexistence", "MAGIC_V2"),
    "SajimV2DualBot": ("v2.sajim_v2_dual_bot", "SajimV2DualBot"),
    "SajimDualOrchestrator": ("v2.dual_orchestrator", "SajimDualOrchestrator"),
}

__all__ = list(_LAZY_EXPORTS)


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        module_name, attr = _LAZY_EXPORTS[name]
        return getattr(importlib.import_module(module_name), attr)
    raise AttributeError(f"module 'v2' has no attribute {name!r}")
