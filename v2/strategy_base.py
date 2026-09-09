"""
========================================================================================
           SAJIM HOLDINGS V2 — PLUGGABLE STRATEGY INTERFACE (v2/strategy_base.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Purpose:
  Defines the standard interface for dynamic, plug-and-play strategy cartridges.
  Decouples alpha generation (signals) from broker execution, risk, and telemetry.
  Allows strategies to be hot-swapped, parameter-tuned, or toggled via WebApp API.
========================================================================================
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class StrategySignal:
    """Standardized institutional signal emitted by any V2 strategy cartridge."""
    symbol: str
    action: str              # "BUY" or "SELL"
    timeframe: str           # "M5", "M15", "H1", "H4"
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float       # e.g. 2.0, 3.0
    confidence: float        # 0.0 to 1.0
    strategy_name: str       # e.g. "YoungSurgeContinuation", "ExhaustionMeanReversion"
    reason: str              # Short narrative rationale
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseStrategyCartridge(ABC):
    """
    Abstract Base Class for all Sajim V2 pluggable strategy cartridges.
    """

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
        self.parameters: Dict[str, Any] = {}
        self.active_trades: Dict[int, StrategySignal] = {}

    @abstractmethod
    def evaluate(
        self,
        symbol: str,
        timeframe: str,
        bars: List[Dict[str, Any]],
        market_info: Dict[str, Any],
    ) -> Optional[StrategySignal]:
        """
        Evaluates historical and current bar data, returning a StrategySignal if entry criteria are met.
        """
        pass

    def get_parameters(self) -> Dict[str, Any]:
        """Returns dictionary of tuneable strategy hyperparameters."""
        return self.parameters.copy()

    def update_parameters(self, new_params: Dict[str, Any]) -> None:
        """Dynamically updates hyperparameters without requiring system reboot."""
        self.parameters.update(new_params)

    def on_trade_opened(self, ticket: int, signal: StrategySignal) -> None:
        """Lifecycle callback when trade execution is confirmed by broker."""
        self.active_trades[ticket] = signal

    def on_trade_closed(self, ticket: int, profit: float) -> None:
        """Lifecycle callback when trade is closed (syncing PnL & streaks)."""
        if ticket in self.active_trades:
            del self.active_trades[ticket]
