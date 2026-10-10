"""
========================================================================================
           SAJIM V2 EXECUTION — ORDER ROUTER & DISPATCH (v2/execution/order_router.py)
========================================================================================
Handles dynamic sizing (core/lot_calculator.py, account-currency aware), MT5 trade
dispatch at a fresh tick price with requote retries and filling-mode fallback,
telemetry blackbox flight logging, and Telegram broadcast bus.

Broker selection is explicit: broker="ctrader" routes to the cTrader bridge, anything
else routes to MT5. There is NO silent mid-session fallback from MT5 to cTrader.
========================================================================================
"""

import logging
from typing import Any, List, Optional

import MetaTrader5 as mt5

from core.lot_calculator import UniversalLotCalculator
from core.trade_flight_recorder import get_flight_recorder
from v2.coexistence import MAGIC_V2
from v2.strategy_base import StrategySignal, BaseStrategyCartridge
from v2.safety import new_entries_allowed
from v2.risk.position_state import PositionStateStore, get_position_store
from v2.execution.mt5_exec import send_market_order

logger = logging.getLogger("SajimV2OrderRouter")

# Conservative V2 sizing defaults: 1% base, 2% hard cap, +10% per win (capped by max_risk)
DEFAULT_BASE_RISK = 0.01
DEFAULT_MAX_RISK = 0.02
DEFAULT_STREAK_RATE = 0.10
MAX_STREAK_STEPS = 4


class V2OrderRouter:
    """Dispatches strategy signals with risk bounds and broker compatibility (MT5 & cTrader)."""

    def __init__(
        self,
        bus: Any,
        base_risk: float = DEFAULT_BASE_RISK,
        max_risk: float = DEFAULT_MAX_RISK,
        streak_rate: float = DEFAULT_STREAK_RATE,
        dry_run: bool = False,
        broker: str = "mt5",
        position_store: Optional[PositionStateStore] = None,
    ):
        self.bus = bus
        self.base_risk = base_risk
        self.max_risk = max_risk
        self.streak_rate = streak_rate
        self.dry_run = dry_run
        self.broker = (broker or "mt5").lower()
        self.store = position_store or get_position_store("v2")
        self._ctrader = None

    @property
    def ctrader(self):
        if self._ctrader is None:
            from core.ctrader_bridge import CTraderBridge
            self._ctrader = CTraderBridge.get_instance()
        return self._ctrader

    def dynamic_risk(self, consecutive_wins: int) -> float:
        streak_mult = (1.0 + self.streak_rate) ** max(0, min(consecutive_wins, MAX_STREAK_STEPS))
        return min(self.max_risk, self.base_risk * streak_mult)

    def dispatch_signal(
        self,
        sig: StrategySignal,
        consecutive_wins: int,
        cartridges: List[BaseStrategyCartridge],
    ) -> bool:
        """Sizes order and sends execution request to MT5 or cTrader."""
        if not new_entries_allowed("V2"):
            return False

        use_ctrader = self.broker == "ctrader"
        account_currency = None
        if use_ctrader:
            acc_info = self.ctrader.get_account_telemetry()
            equity = acc_info.get("equity")
            account_currency = acc_info.get("currency")
            if not acc_info.get("is_connected") or not equity:
                logger.error("[V2] cTrader bridge not connected / no equity; order skipped.")
                return False
        else:
            acc = mt5.account_info()
            if not acc:
                logger.error(f"[V2] mt5.account_info() is None; order on {sig.symbol} skipped: {mt5.last_error()}")
                return False
            equity = acc.equity
            account_currency = acc.currency

        dynamic_risk = self.dynamic_risk(consecutive_wins)

        try:
            lot, risk_cash, specs = UniversalLotCalculator.calculate_lot(
                symbol=sig.symbol,
                equity=equity,
                risk_fraction=dynamic_risk,
                entry_price=sig.entry_price,
                stop_price=sig.stop_loss,
                account_currency=account_currency,
            )
        except ValueError as e:
            logger.error(f"[V2] Sizing failed for {sig.symbol}: {e}")
            return False

        if lot <= 0:
            logger.info(f"[V2] {sig.symbol}: {specs.get('rejected', 'cannot size within risk budget')}; signal skipped.")
            return False

        # Determine bot label for cTrader
        strat_lower = sig.strategy_name.lower()
        if "revert" in strat_lower or "exhaustion" in strat_lower:
            bot_label = "SAJIM_V2_REVERT"
        elif "surge" in strat_lower or "continuation" in strat_lower:
            bot_label = "SAJIM_V2_SURGE"
        else:
            bot_label = "SAJIM_V2"

        if use_ctrader:
            if self.dry_run:
                logger.info(
                    f"[DRY RUN CTRADER] [{bot_label}] {sig.strategy_name} | would {sig.action} {lot} {sig.symbol} "
                    f"| SL: {sig.stop_loss:.5f} | TP: {sig.take_profit:.5f} | Risk {dynamic_risk*100:.2f}%"
                )
                return True
            res = self.ctrader.send_order(
                symbol=sig.symbol,
                action=sig.action,
                volume=float(lot),
                entry_price=float(sig.entry_price),
                sl=float(sig.stop_loss),
                tp=float(sig.take_profit),
                label=bot_label,
                comment=f"Sajim_{sig.strategy_name[:12]}",
            )
            if res.get("success") and not res.get("simulated"):
                ticket = res["ticket"]
                logger.info(
                    f"[cTrader ORDER DISPATCHED] #{ticket} [{bot_label}] {sig.action} {lot} {sig.symbol} "
                    f"| Strategy: {sig.strategy_name}"
                )
                for cart in cartridges:
                    if cart.name == sig.strategy_name:
                        cart.on_trade_opened(ticket, sig)
                return True
            logger.error(f"[V2] cTrader order not executed on {sig.symbol}: {res.get('error') or res.get('status')}")
            return False

        cmt_text = "Scalping_Opp" if sig.timeframe == "M1" else f"Sajim_V2_{sig.strategy_name[:10]}"
        ok, res, fill_price = send_market_order(
            symbol=sig.symbol,
            action=sig.action,
            volume=float(lot),
            sl=float(sig.stop_loss),
            tp=float(sig.take_profit),
            magic=MAGIC_V2,
            comment=cmt_text,
            dry_run=self.dry_run,
            bot_name="V2",
        )
        if not ok:
            return False
        if self.dry_run:
            logger.info(
                f"[DRY RUN MT5] {sig.strategy_name} | {sig.action} {lot} {sig.symbol} | Risk {dynamic_risk*100:.2f}% "
                f"| Reason: {sig.reason}"
            )
            return True

        ticket = int(res.order)
        entry_px = float(fill_price or sig.entry_price)
        self.store.record_entry(ticket, sig.symbol, entry_px, float(sig.stop_loss), bot="V2")
        logger.info(
            f"[🚀 V2 ORDER EXECUTED] #{ticket} {sig.action} {lot} {sig.symbol} @ {entry_px:.5f} | "
            f"SL: {sig.stop_loss:.5f} | TP: {sig.take_profit:.5f} | Strategy: {sig.strategy_name}"
        )
        try:
            self.bus.broadcast_v2_trade_executed(
                ticket=ticket,
                symbol=sig.symbol,
                action=sig.action,
                lot=lot,
                entry=entry_px,
                sl=sig.stop_loss,
                tp=sig.take_profit,
                strategy_name=sig.strategy_name,
                maturity_info=sig.metadata,
                timeframe=sig.timeframe,
            )
        except Exception as b_err:
            logger.warning(f"Failed to broadcast V2 trade execution: {b_err}")

        try:
            get_flight_recorder().record_entry(
                ticket=ticket,
                symbol=sig.symbol,
                action=sig.action,
                volume=float(lot),
                entry_price=entry_px,
                sl=float(sig.stop_loss),
                tp=float(sig.take_profit),
                strategy_name=sig.strategy_name,
                metadata=sig.metadata,
            )
        except Exception as fr_err:
            logger.warning(f"Failed to record flight entry: {fr_err}")

        for cart in cartridges:
            if cart.name == sig.strategy_name:
                cart.on_trade_opened(ticket, sig)
        return True
