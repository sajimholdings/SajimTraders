"""
========================================================================================
           SAJIM V2 RISK — TRAILING RATCHET & DEFENSE SHIELDS (v2/risk/ratchet.py)
========================================================================================
Implements multi-stage asymmetric capital defense:
  1. Stage 0 Breakeven Shield (+0.35R) -> Move SL to Open + 0.05R ($0 Risk).
  2. Stage 0B Adverse Euthanasia (-0.35R) -> Cut early if adverse momentum turns.
  3. Stage 0C Kinetic Decay Exit (>= +0.65R) -> Cash out when momentum dissipates.
  4. Stage 1 Profit Lock (+1.50R) -> Lock +0.30R.
  5. Stage 2 Profit Lock (+2.20R) -> Lock +1.00R.
  6. Hummingbird Peak Harvest -> Microsecond peak profit extraction.
Modular Architecture: Strictly < 240 lines.
========================================================================================
"""

import logging
from typing import Any, Dict, Set
import MetaTrader5 as mt5

from core.trade_flight_recorder import get_flight_recorder
from core.beep_processor import BeepProcessor
from v2.coexistence import MAGIC_V2
from v2.risk.hummingbird import HummingbirdEvaluator

logger = logging.getLogger("SajimV2Ratchet")


class V2PositionRiskManager:
    """Manages active trade ratchets, defense shields, and profit harvests."""

    def __init__(
        self,
        bus: Any,
        trailing_ratchet_state: Dict[int, str],
        harvested_tickets: Set[int],
        pending_reentry_symbols: Set[str],
        hummingbird_harvest_enabled: bool = True,
        hummingbird_harvest_mode: str = "FULL",
        hummingbird_partial_ratio: float = 0.80,
        kinetic_exit_enabled: bool = True,
        dry_run: bool = False,
    ):
        self.bus = bus
        self.trailing_ratchet_state = trailing_ratchet_state
        self.harvested_tickets = harvested_tickets
        self.pending_reentry_symbols = pending_reentry_symbols
        self.hummingbird_harvest_enabled = hummingbird_harvest_enabled
        self.hummingbird_harvest_mode = hummingbird_harvest_mode.upper()
        self.hummingbird_partial_ratio = hummingbird_partial_ratio
        self.kinetic_exit_enabled = kinetic_exit_enabled
        self.dry_run = dry_run

    def manage_positions(self) -> None:
        """Evaluates all active Magic 888222 positions for ratchet & harvest."""
        positions = [p for p in (mt5.positions_get() or []) if p.magic == MAGIC_V2]
        for pos in positions:
            sym_info = mt5.symbol_info(pos.symbol)
            if not sym_info:
                continue

            is_buy = pos.type == mt5.POSITION_TYPE_BUY
            cur_price = sym_info.bid if is_buy else sym_info.ask
            open_price = pos.price_open
            sl_price = pos.sl

            init_risk = abs(open_price - sl_price) if sl_price > 0 else (sym_info.point * 150)
            if init_risk <= 0:
                continue

            profit_dist = (cur_price - open_price) if is_buy else (open_price - cur_price)
            profit_r = profit_dist / init_risk
            current_ratchet = self.trailing_ratchet_state.get(pos.ticket, "INITIAL")

            # Micro-telemetry tick logging
            try:
                get_flight_recorder().record_tick(
                    ticket=pos.ticket,
                    current_price=float(cur_price),
                    current_profit=float(pos.profit),
                    status_tag=f"RATCHET_{current_ratchet}",
                )
            except Exception:
                pass

            # 0. Early Breakeven Shield (+0.35R)
            if profit_r >= 0.35 and current_ratchet == "INITIAL":
                be_offset = max(sym_info.point * 15, init_risk * 0.05)
                new_sl = (open_price + be_offset) if is_buy else (open_price - be_offset)
                mod_req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": float(new_sl),
                    "tp": float(pos.tp),
                }
                res = mt5.order_send(mod_req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"[🛡️ V2 BREAKEVEN SHIELD] #{pos.ticket} {pos.symbol} moved to BE (+0.05R). Zero downside risk!")
                    self.trailing_ratchet_state[pos.ticket] = "STAGE_0_BE"
                    current_ratchet = "STAGE_0_BE"
                    try:
                        self.bus.broadcast_ratchet_update(
                            ticket=pos.ticket,
                            symbol=pos.symbol,
                            stage="BREAK_EVEN",
                            new_sl=float(new_sl),
                            r_level=f"+{profit_r:.2f}R",
                        )
                    except Exception:
                        pass

            # 0B. Early Reversal Euthanasia (-0.35R)
            if profit_r <= -0.35:
                rates_rev = mt5.copy_rates_from_pos(pos.symbol, mt5.TIMEFRAME_M1, 0, 5)
                if rates_rev is not None and len(rates_rev) >= 3:
                    bar_0, bar_1 = rates_rev[-1], rates_rev[-2]
                    is_adverse_turn = False
                    if is_buy:
                        b0, b1 = float(bar_0['open'] - bar_0['close']), float(bar_1['open'] - bar_1['close'])
                        if b0 > 0 and b1 > 0 and float(bar_0['close']) < float(bar_1['low']):
                            is_adverse_turn = True
                    else:
                        b0, b1 = float(bar_0['close'] - bar_0['open']), float(bar_1['close'] - bar_1['open'])
                        if b0 > 0 and b1 > 0 and float(bar_0['close']) > float(bar_1['high']):
                            is_adverse_turn = True

                    if is_adverse_turn:
                        order_type_close = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
                        for filling in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
                            close_req = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "position": pos.ticket,
                                "symbol": pos.symbol,
                                "volume": float(pos.volume),
                                "type": order_type_close,
                                "price": float(cur_price),
                                "deviation": 30,
                                "magic": MAGIC_V2,
                                "comment": "Adverse_Cut",
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": filling,
                            }
                            res = mt5.order_send(close_req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                logger.info(f"[🚨 EARLY CUT] #{pos.ticket} cut at -{abs(profit_r):.2f}R on momentum turn.")
                                self.trailing_ratchet_state.pop(pos.ticket, None)
                                break
                        continue

            # 0C. Kinetic Momentum Decrement & Exhaustion Exit (>= +0.65R)
            if self.kinetic_exit_enabled and profit_r >= 0.65 and (profit_r < 1.50 or not self.hummingbird_harvest_enabled):
                rates = mt5.copy_rates_from_pos(pos.symbol, mt5.TIMEFRAME_M1, 0, 15)
                should_fast_exit = False
                exit_reason = ""
                if rates is not None and len(rates) >= 2:
                    action_dir = "BUY" if is_buy else "SELL"
                    should_fast_exit, decay_reason, _ = BeepProcessor.evaluate_kinetic_decay(
                        bars=rates,
                        action=action_dir,
                        atr=None,
                        adverse_wick_threshold=0.40,
                        dissipation_threshold=0.70,
                    )
                    if should_fast_exit:
                        exit_reason = decay_reason

                if should_fast_exit:
                    if self.dry_run:
                        logger.info(f"[DRY RUN KINETIC HARVEST] #{pos.ticket} {pos.symbol} (+{profit_r:.2f}R): {exit_reason}")
                        continue
                    order_type_close = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
                    for filling in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
                        close_req = {
                            "action": mt5.TRADE_ACTION_DEAL,
                            "position": pos.ticket,
                            "symbol": pos.symbol,
                            "volume": float(pos.volume),
                            "type": order_type_close,
                            "price": float(cur_price),
                            "deviation": 30,
                            "magic": MAGIC_V2,
                            "comment": f"Kinetic_{exit_reason[:15]}",
                            "type_time": mt5.ORDER_TIME_GTC,
                            "type_filling": filling,
                        }
                        res = mt5.order_send(close_req)
                        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                            logger.info(f"[⚡ KINETIC HARVEST] #{pos.ticket} closed at peak (+{profit_r:.2f}R) | Reason: {exit_reason}")
                            self.trailing_ratchet_state.pop(pos.ticket, None)
                            break
                    continue

            # 1. Hummingbird Peak Harvest (+1.5R to +2.85R)
            if self.hummingbird_harvest_enabled and profit_r >= 1.50:
                should_harvest, exhaust_reason = HummingbirdEvaluator.check_exhaustion(pos, profit_r, sym_info)
                if should_harvest:
                    is_full = (self.hummingbird_harvest_mode == "FULL") or (pos.ticket in self.harvested_tickets)
                    close_vol = pos.volume if is_full else round(max(0.01, pos.volume * self.hummingbird_partial_ratio), 2)
                    close_type = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
                    close_price = sym_info.bid if is_buy else sym_info.ask

                    for filling in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
                        close_req = {
                            "action": mt5.TRADE_ACTION_DEAL,
                            "position": pos.ticket,
                            "symbol": pos.symbol,
                            "volume": float(close_vol),
                            "type": close_type,
                            "price": float(close_price),
                            "deviation": 20,
                            "magic": MAGIC_V2,
                            "comment": "Hummingbird_Peak",
                            "type_time": mt5.ORDER_TIME_GTC,
                            "type_filling": filling,
                        }
                        res = mt5.order_send(close_req)
                        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                            logger.info(f"[🦅 HUMMINGBIRD HARVEST] #{pos.ticket} closed at peak (+{profit_r:.2f}R): {exhaust_reason}")
                            self.trailing_ratchet_state.pop(pos.ticket, None)
                            break
                    continue

            # 2. Stage 2 Ratchet: Lock in +1.0R Net Profit at +2.2R
            if profit_r >= 2.20 and current_ratchet != "STAGE_2_LOCK":
                new_sl = (open_price + (1.0 * init_risk)) if is_buy else (open_price - (1.0 * init_risk))
                mod_req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": float(new_sl),
                    "tp": float(pos.tp),
                }
                res = mt5.order_send(mod_req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"[🔒 V2 PROFIT LOCK] Locked +1.0R Net Profit on #{pos.ticket} {pos.symbol} (+{profit_r:.2f}R).")
                    self.trailing_ratchet_state[pos.ticket] = "STAGE_2_LOCK"

            # Stage 1 Ratchet: Move to Profit Lock +0.30R at +1.5R
            elif profit_r >= 1.50 and current_ratchet in ("INITIAL", "STAGE_0_BE"):
                new_sl = (open_price + (0.30 * init_risk)) if is_buy else (open_price - (0.30 * init_risk))
                mod_req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": float(new_sl),
                    "tp": float(pos.tp),
                }
                res = mt5.order_send(mod_req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"[🛡️ V2 PROFIT SECURED] Secured +0.30R on #{pos.ticket} {pos.symbol} (+{profit_r:.2f}R).")
                    self.trailing_ratchet_state[pos.ticket] = "STAGE_1_BE"
