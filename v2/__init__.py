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
  └── v2.api          : Real-time Telemetry, WebSocket Feeds & WebApp Bridge
========================================================================================
"""

from v2.trend_duration_engine import TrendDurationEngine
from v2.strategy_base import BaseStrategyCartridge, StrategySignal
from v2.coexistence import CoexistenceGatekeeper, MAGIC_V1, MAGIC_V2
from v2.sajim_v2_dual_bot import SajimV2DualBot
from v2.dual_orchestrator import SajimDualOrchestrator

__all__ = [
    "TrendDurationEngine",
    "BaseStrategyCartridge",
    "StrategySignal",
    "CoexistenceGatekeeper",
    "MAGIC_V1",
    "MAGIC_V2",
    "SajimV2DualBot",
    "SajimDualOrchestrator",
]
