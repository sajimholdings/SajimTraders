"""
========================================================================================
           SAJIM V2 RISK — TRAILING RATCHET & DEFENSE SHIELDS (v2/risk/ratchet.py)
========================================================================================
Implements multi-stage asymmetric capital defense (thresholds: v2/risk/constants.py):
  1. Stage 0 Breakeven Shield (+0.35R) -> Move SL to Open + 0.05R ($0 Risk).
  2. Stage 0B Adverse Euthanasia (-0.35R) -> Cut early if adverse momentum turns.
  3. Stage 0C Kinetic Decay Exit (>= +0.65R) -> Cash out when momentum dissipates
     (requires the private BEEP processor; disabled with a warning if absent).
  4. Stage 1 Profit Lock (+1.50R) -> Lock +0.30R.
  5. Stage 2 Profit Lock (+2.20R) -> Lock +1.00R.
  6. Hummingbird Peak Harvest -> Peak profit extraction.

R-multiples are measured against the INITIAL risk recorded at entry
(v2/risk/position_state.py, persisted with the ratchet stage in state/v2_positions.json).
In dry run NOTHING is sent to the broker; "[DRY RUN] would ..." is logged instead.
========================================================================================
"""

import logging
from typing import Any, Dict, Optional, Set, Tuple
import MetaTrader5 as mt5

from core.trade_flight_recorder import get_flight_recorder
from v2.coexistence import MAGIC_V2
from v2.risk import constants as RC
from v2.risk.hummingbird import HummingbirdEvaluator
from v2.risk.position_state import PositionStateStore, get_position_store
from v2.execution.mt5_exec import close_position, modify_sltp, floor_volume

try:
    from core.beep_processor import BeepProcessor  # private BEEP module (git-ignored)
except ImportError:  # pragma: no cover - depends on private modules
    BeepProcessor = None

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
        position_store: Optional[PositionStateStore] = None,
    ):
        self.bus = bus
        self.trailing_ratchet_state = trailing_ratchet_state
        self.harvested_tickets = harvested_tickets
        self.pending_reentry_symbols = pending_reentry_symbols
        self.hummingbird_harvest_enabled = hummingbird_harvest_enabled
        self.hummingbird_harvest_mode = hummingbird_harvest_mode.upper()
        self.hummingbird_partial_ratio = hummingbird_partial_ratio
        self.kinetic_exit_enabled = kinetic_exit_enabled
        if self.kinetic_exit_enabled and BeepProcessor is None:
            logger.warning("Kinetic decay exit disabled: private module core.beep_processor is not available.")
            self.kinetic_exit_enabled = False
        self.dry_run = dry_run
        self.store = position_store or get_position_store("v2")

        # Restore persisted ratchet stages / harvest flags after a restart
        for ticket, stage in self.store.stages().items():
            self.trailing_ratchet_state.setdefault(ticket, stage)
        self.harvested_tickets.update(self.store.harvested_tickets())

        self._dry_run_actions: Set[Tuple[int, str]] = set()
        self._dry_run_closed: Set[int] = set()
        self._unknown_risk_warned: Set[int] = set()

    # ------------------------------------------------------------------ helpers
    def _set_stage(self, ticket: int, stage: str) -> None:
        self.trailing_ratchet_state[ticket] = stage
        if not self.dry_run:
            self.store.set_stage(ticket, stage)

    def _dry_once(self, ticket: int, action: str) -> bool:
        key = (int(ticket), action)
        if key in self._dry_run_actions:
            return False
        self._dry_run_actions.add(key)
        return True

    def _modify(self, pos: Any, new_sl: float, tag: str, digits: Optional[int]) -> bool:
        if self.dry_run and not self._dry_once(pos.ticket, tag):
            return False
        return modify_sltp(pos, new_sl, pos.tp, dry_run=self.dry_run, bot_name="V2", digits=digits)

    def _close(self, pos: Any, comment: str, volume: Optional[float] = None) -> bool:
        if self.dry_run:
            if not self._dry_once(pos.ticket, f"close:{comment}"):
                return False
            close_position(pos, magic=MAGIC_V2, comment=comment, dry_run=True, volume=volume, bot_name="V2")
            if volume is None or volume >= pos.volume:
                self._dry_run_closed.add(pos.ticket)
            return True
        return close_position(pos, magic=MAGIC_V2, comment=comment, dry_run=False, volume=volume,
                              bot_name="V2", deviation=30)

    def _closed(self, pos: Any) -> None:
        self.trailing_ratchet_state.pop(pos.ticket, None)
        if not self.dry_run:
            self.store.forget(pos.ticket)

    # --------------------------------------------------------------- management
    def manage_positions(self) -> None:
        """Evaluates all active Magic 888222 positions for ratchet & harvest."""
        all_positions = mt5.positions_get()
        if all_positions is None:
            return  # disconnected: keep state untouched
        positions = [p for p in all_positions if p.magic == MAGIC_V2]
        open_tickets = {p.ticket for p in positions}
        self.store.prune(open_tickets)
        for stale in [t for t in self.trailing_ratchet_state if t not in open_tickets]:
            self.trailing_ratchet_state.pop(stale, None)
        self._dry_run_closed &= open_tickets

        for pos in positions:
            if pos.ticket in self._dry_run_closed:
                continue
            sym_info = mt5.symbol_info(pos.symbol)
            if not sym_info:
                continue

            is_buy = pos.type == mt5.POSITION_TYPE_BUY
            cur_price = sym_info.bid if is_buy else sym_info.ask
            open_price = pos.price_open
            digits = getattr(sym_info, "digits", None)

            init_risk = self.store.initial_risk(pos, mt5_module=mt5)
            if not init_risk or init_risk <= 0:
                if pos.ticket not in self._unknown_risk_warned:
                    self._unknown_risk_warned.add(pos.ticket)
                    logger.warning(
                        f"[V2] #{pos.ticket} {pos.symbol}: initial risk unknown; R-based management skipped "
                        f"(broker SL/TP remain in force)."
                    )
                continue

            profit_dist = (cur_price - open_price) if is_buy else (open_price - cur_price)
            profit_r = profit_dist / init_risk
            current_ratchet = self.trailing_ratchet_state.get(pos.ticket, self.store.get_stage(pos.ticket))

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
            if profit_r >= RC.V2_BE_SHIELD_TRIGGER_R and current_ratchet == "INITIAL":
                be_offset = max(sym_info.point * 15, init_risk * RC.V2_BE_SHIELD_OFFSET_R)
                new_sl = (open_price + be_offset) if is_buy else (open_price - be_offset)
                if self._modify(pos, new_sl, "STAGE_0_BE", digits):
                    logger.info(f"[🛡️ V2 BREAKEVEN SHIELD]{' [DRY RUN]' if self.dry_run else ''} #{pos.ticket} {pos.symbol} SL -> BE (+{RC.V2_BE_SHIELD_OFFSET_R}R).")
                    self._set_stage(pos.ticket, "STAGE_0_BE")
                    current_ratchet = "STAGE_0_BE"
                    if not self.dry_run:
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
            if profit_r <= RC.V2_EARLY_CUT_R:
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
                        if self._close(pos, "Adverse_Cut"):
                            logger.info(f"[🚨 EARLY CUT]{' [DRY RUN]' if self.dry_run else ''} #{pos.ticket} cut at -{abs(profit_r):.2f}R on momentum turn.")
                            self._closed(pos)
                        continue

            # 0C. Kinetic Momentum Decrement & Exhaustion Exit (>= +0.65R)
            if (self.kinetic_exit_enabled and profit_r >= RC.V2_KINETIC_MIN_R
                    and (profit_r < RC.HUMMINGBIRD_MIN_R or not self.hummingbird_harvest_enabled)):
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
                    if self._close(pos, f"Kinetic_{exit_reason[:15]}"):
                        logger.info(f"[⚡ KINETIC HARVEST]{' [DRY RUN]' if self.dry_run else ''} #{pos.ticket} closed (+{profit_r:.2f}R) | Reason: {exit_reason}")
                        self._closed(pos)
                    continue

            # 1. Hummingbird Peak Harvest (>= +1.5R)
            if self.hummingbird_harvest_enabled and profit_r >= RC.HUMMINGBIRD_MIN_R:
                should_harvest, exhaust_reason = HummingbirdEvaluator.check_exhaustion(pos, profit_r, sym_info)
                if should_harvest:
                    is_full = (self.hummingbird_harvest_mode == "FULL") or (pos.ticket in self.harvested_tickets)
                    close_vol = None
                    if not is_full:
                        close_vol = floor_volume(pos.volume * self.hummingbird_partial_ratio, sym_info)
                        if close_vol <= 0 or close_vol >= pos.volume:
                            close_vol = None  # cannot split below broker min lot -> close all
                    if self._close(pos, "Hummingbird_Peak", volume=close_vol):
                        logger.info(f"[🦅 HUMMINGBIRD HARVEST]{' [DRY RUN]' if self.dry_run else ''} #{pos.ticket} closed {close_vol or pos.volume} at peak (+{profit_r:.2f}R): {exhaust_reason}")
                        if close_vol is None:
                            self._closed(pos)
                        else:
                            self.harvested_tickets.add(pos.ticket)
                            if not self.dry_run:
                                self.store.mark_harvested(pos.ticket)
                    continue

            # 2. Stage 2 Ratchet: Lock in +1.0R Net Profit at +2.2R
            if profit_r >= RC.V2_STAGE2_TRIGGER_R and current_ratchet != "STAGE_2_LOCK":
                lock = RC.V2_STAGE2_LOCK_R * init_risk
                new_sl = (open_price + lock) if is_buy else (open_price - lock)
                if self._modify(pos, new_sl, "STAGE_2_LOCK", digits):
                    logger.info(f"[🔒 V2 PROFIT LOCK]{' [DRY RUN]' if self.dry_run else ''} Locked +{RC.V2_STAGE2_LOCK_R}R on #{pos.ticket} {pos.symbol} (+{profit_r:.2f}R).")
                    self._set_stage(pos.ticket, "STAGE_2_LOCK")

            # Stage 1 Ratchet: Move to Profit Lock +0.30R at +1.5R
            elif profit_r >= RC.V2_STAGE1_TRIGGER_R and current_ratchet in ("INITIAL", "STAGE_0_BE"):
                lock = RC.V2_STAGE1_LOCK_R * init_risk
                new_sl = (open_price + lock) if is_buy else (open_price - lock)
                if self._modify(pos, new_sl, "STAGE_1_BE", digits):
                    logger.info(f"[🛡️ V2 PROFIT SECURED]{' [DRY RUN]' if self.dry_run else ''} Secured +{RC.V2_STAGE1_LOCK_R}R on #{pos.ticket} {pos.symbol} (+{profit_r:.2f}R).")
                    self._set_stage(pos.ticket, "STAGE_1_BE")
