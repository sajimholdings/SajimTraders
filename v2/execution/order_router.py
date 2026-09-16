"""
========================================================================================
           SAJIM V2 EXECUTION — ORDER ROUTER & DISPATCH (v2/execution/order_router.py)
========================================================================================
Handles dynamic sizing, micro-lot safeguards (0.01 on accounts < $100), MT5 trade
dispatch, telemetry blackbox flight logging, and Telegram broadcast bus.
Modular Architecture: Strictly < 160 lines.
========================================================================================
"""

import logging
from typing import Any, List
import MetaTrader5 as mt5

from core.lot_calculator import UniversalLotCalculator
from core.trade_flight_recorder import get_flight_recorder
from core.ctrader_bridge import CTraderBridge
from v2.coexistence import MAGIC_V2
from v2.strategy_base import StrategySignal, BaseStrategyCartridge

logger = logging.getLogger("SajimV2OrderRouter")


class V2OrderRouter:
    """Dispatches strategy signals with risk bounds and broker compatibility (MT5 & cTrader)."""

    def __init__(
        self,
        bus: Any,
        base_risk: float = 0.05,
        max_risk: float = 0.08,
        streak_rate: float = 0.25,
        dry_run: bool = False,
        broker: str = "auto",
    ):
        self.bus = bus
        self.base_risk = base_risk
        self.max_risk = max_risk
        self.streak_rate = streak_rate
        self.dry_run = dry_run
        self.broker = broker.lower()
        self.ctrader = CTraderBridge.get_instance()

    def dispatch_signal(
        self,
        sig: StrategySignal,
        consecutive_wins: int,
        cartridges: List[BaseStrategyCartridge],
    ) -> bool:
        """Sizes order and sends execution request to MT5 or cTrader."""
        # Determine active broker backend
        use_ctrader = self.broker == "ctrader" or not hasattr(mt5, "account_info")

        if use_ctrader:
            acc_info = self.ctrader.get_account_telemetry()
            equity = acc_info["equity"]
        else:
            acc = mt5.account_info()
            if not acc:
                if self.broker == "auto":
                    use_ctrader = True
                    acc_info = self.ctrader.get_account_telemetry()
                    equity = acc_info["equity"]
                else:
                    return False
            else:
                equity = acc.equity

        # Dynamic Sizing based on winning streaks
        streak_mult = (1.0 + self.streak_rate) ** min(consecutive_wins, 4)
        dynamic_risk = min(self.max_risk, self.base_risk * streak_mult)

        lot, risk_cash, specs = UniversalLotCalculator.calculate_lot(
            symbol=sig.symbol,
            equity=equity,
            risk_fraction=dynamic_risk,
            entry_price=sig.entry_price,
            stop_price=sig.stop_loss,
        )

        # Micro-lot safeguard for accounts < $100
        if equity < 100.0:
            lot = 0.01

        # Determine bot label for cTrader
        strat_lower = sig.strategy_name.lower()
        if "revert" in strat_lower or "exhaustion" in strat_lower:
            bot_label = "SAJIM_V2_REVERT"
        elif "surge" in strat_lower or "continuation" in strat_lower:
            bot_label = "SAJIM_V2_SURGE"
        else:
            bot_label = "SAJIM_V1"

        if self.dry_run:
            logger.info(
                f"[DRY RUN {self.broker.upper()}] [{bot_label}] {sig.strategy_name} | {sig.action} {lot} {sig.symbol} "
                f"@ {sig.entry_price:.5f} | SL: {sig.stop_loss:.5f} | TP: {sig.take_profit:.5f} | Reason: {sig.reason}"
            )
            return True

        if use_ctrader:
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
            if res.get("success"):
                ticket = res["ticket"]
                logger.info(
                    f"[cTrader ORDER DISPATCHED] #{ticket} [{bot_label}] {sig.action} {lot} {sig.symbol} "
                    f"@ {sig.entry_price:.5f} | Strategy: {sig.strategy_name}"
                )
                for cart in cartridges:
                    if cart.name == sig.strategy_name:
                        cart.on_trade_opened(ticket, sig)
                return True
            return False

        cmt_text = "Scalping_Opp" if sig.timeframe == "M1" else f"Sajim_V2_{sig.strategy_name[:10]}"
        for filling in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
            order_req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": sig.symbol,
                "volume": float(lot),
                "type": order_type,
                "price": float(sig.entry_price),
                "sl": float(sig.stop_loss),
                "tp": float(sig.take_profit),
                "deviation": 20,
                "magic": MAGIC_V2,
                "comment": cmt_text,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }
            res = mt5.order_send(order_req)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(
                    f"[🚀 V2 ORDER EXECUTED] #{res.order} {sig.action} {lot} {sig.symbol} @ {sig.entry_price:.5f} | "
                    f"SL: {sig.stop_loss:.5f} | TP: {sig.take_profit:.5f} | Strategy: {sig.strategy_name}"
                )
                try:
                    self.bus.broadcast_v2_trade_executed(
                        ticket=res.order,
                        symbol=sig.symbol,
                        action=sig.action,
                        lot=lot,
                        entry=sig.entry_price,
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
                        ticket=res.order,
                        symbol=sig.symbol,
                        action=sig.action,
                        volume=float(lot),
                        entry_price=float(sig.entry_price),
                        sl=float(sig.stop_loss),
                        tp=float(sig.take_profit),
                        strategy_name=sig.strategy_name,
                        metadata=sig.metadata,
                    )
                except Exception as fr_err:
                    logger.warning(f"Failed to record flight entry: {fr_err}")

                for cart in cartridges:
                    if cart.name == sig.strategy_name:
                        cart.on_trade_opened(res.order, sig)
                return True
            elif res and "Unsupported filling mode" in (res.comment or ""):
                continue
            else:
                err = res.comment if res else mt5.last_error()
                logger.warning(f"[!] V2 Order failed on {sig.symbol}: {err}")
                return False

        return False
