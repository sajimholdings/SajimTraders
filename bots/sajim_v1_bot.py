"""
========================================================================================
            SAJIM HOLDINGS — SAJIM V1 BOT (bots/sajim_v1_bot.py)
========================================================================================
Chief Architect: Jimmy Mathu
Canonical 7-Stage Quantitative Pipeline:
    DATA -> BEEP -> SIGNAL -> SAJIM -> ENTRY -> MANAGEMENT -> PNL

This engine executes Stages 4, 5, 6, and 7:
  [4] SAJIM       : Portfolio diversification, loss cooldown, dynamic scale-invariant sizing
  [5] ENTRY       : Robust MT5 order dispatch with margin-cap & filling mode fallback
  [6] MANAGEMENT  : Two-stage trailing ratchet (+1.5R BE, +2.2R Lock +1.0R Net Profit)
  [7] PNL         : Deal history synchronizer, continuous compounding, formulaic step-back
========================================================================================
"""

import os
import sys
import time
import math
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Set, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, BASE_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "vault")):
    if p not in sys.path:
        sys.path.insert(0, p)

import MetaTrader5 as mt5
from core.beep_signal_engine import BeepSignal, BeepSignalEngine
from core.lot_calculator import UniversalLotCalculator
from core.beep_broadcast import BeepBroadcastBus
from core.sajim_regime_algos import SajimChameleonClassifier
from core.dealer_state_space import DealerMicrostructureEngine, ThreeCandleTickConfirmationEngine
from core.whitelist_manager import get_whitelist_manager
from core.mt5_login import ensure_account
from v2.safety import (
    new_entries_allowed, is_cent_account, to_major_units, from_major_units,
    DailyDrawdownGuard, utc_now, utc_day_start,
)
from v2.risk import constants as RC
from v2.risk.position_state import get_position_store
from v2.execution.mt5_exec import send_market_order, close_position, modify_sltp, floor_volume

logger = logging.getLogger("SajimV1Bot")

MAGIC_V1 = 777999


# PILLAR 1: THE CLEAN PLATE PROTOCOL — TOXIC ASSET BLACKLIST
# Single source of truth: config/master_trading_whitelist.json (via core/whitelist_manager.py).
# This module-level set is a backward-compatible snapshot of the symbol-level entries; live
# checks call the whitelist manager (which also enforces per-timeframe SYMBOL_TF entries).
def _load_toxic_blacklist() -> Set[str]:
    try:
        return set(get_whitelist_manager().get_toxic_blacklist())
    except Exception as e:
        logger.error(f"Could not load toxic blacklist from master whitelist: {e}")
        return set()


TOXIC_BLACKLIST = _load_toxic_blacklist()

# CAPITAL MILESTONE STANDBY GATE (thresholds in USD; cent equity is normalised to USD)
# Benching volatile / high-notional assets until account reaches safe capital milestone
STANDBY_ASSETS_USD = {
    "XAUUSD": 1000.0,    # Gold benched on STANDBY until equity >= $1,000 USD (= 100,000 USC)
}


class SajimV1Bot:
    """
    Sajim V1 Execution, Risk & Capital Management Engine.
    Subscribes to BEEP Signals and manages the complete trade lifecycle.
    """

    def __init__(
        self,
        max_concurrent_positions: int = 5,     # Focused, rock-solid exposure (5 assets max)
        base_risk_fraction: float = 0.015,     # 1.5% base risk per trade (~$5.40 on $360 balance)
        streak_expansion_rate: float = 0.10,   # +10% expansion on verified streaks
        max_risk_fraction: float = 0.020,      # 2.0% absolute hard risk cap
        cooldown_minutes: int = 20,            # Loss recovery cooldown
        max_daily_drawdown_usd: float = 35.0,  # Hard cap in USD (converted to USC on cent accounts)
        max_daily_drawdown_pct: float = 0.05,  # 5% of UTC start-of-day equity (whichever is smaller)
        vip_extra_slots: int = 0,              # Opt-in extra concurrency slots for XAUUSD/GBPUSD/EURUSD
        dry_run: bool = False,
    ):
        self.terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
        self.max_positions = max_concurrent_positions
        self.base_risk = base_risk_fraction
        self.streak_rate = streak_expansion_rate
        self.max_risk = max_risk_fraction
        self.cooldown_minutes = cooldown_minutes
        self.max_daily_drawdown_usd = max_daily_drawdown_usd
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        self.vip_extra_slots = max(0, int(vip_extra_slots))
        self.dry_run = dry_run
        self.daily_guard = DailyDrawdownGuard("v1", max_dd_pct=max_daily_drawdown_pct)
        # Persistent per-ticket state: initial risk (for R-multiples), partial-harvest flags
        self.position_store = get_position_store("v1")
        self.bus = BeepBroadcastBus()
        self.beep_engine = BeepSignalEngine()

        # Compounding & Performance State
        self.consecutive_wins = 0
        self.cluster_streaks: Dict[str, int] = {}
        self.partially_closed_tickets: Set[int] = set()
        self.harvested_tickets: Set[int] = set(self.position_store.harvested_tickets())
        self.pending_reentry_symbols: Set[str] = set()
        self.total_trades_taken = 0
        self.session_pnl = 0.0
        self.last_deal_check_time = datetime.now() - timedelta(hours=2)
        self.symbol_cooldowns: Dict[str, datetime] = {}
        self.processed_deal_tickets: Set[int] = set()
        self.dealer_engine = DealerMicrostructureEngine()
        self.pre_entry_hook = None
        # Dry-run bookkeeping (never touches the broker)
        self._dry_run_actions: Set[Tuple[int, str]] = set()
        self.dry_run_closed: Set[int] = set()
        self._unknown_risk_warned: Set[int] = set()
        # Realized P&L of partially closed positions (streaks count full closes only)
        self._partial_pnl: Dict[int, float] = {}

    def get_cluster(self, symbol: str) -> str:
        """Returns the macroeconomic currency cluster for the symbol."""
        s = symbol.upper()
        if "XAU" in s or "XAG" in s:
            return "METALS"
        elif "NZD" in s:
            return "NZD"
        elif "JPY" in s:
            return "JPY"
        elif "GBP" in s:
            return "GBP"
        elif "EUR" in s:
            return "EUR"
        elif "AUD" in s:
            return "AUD"
        elif "CAD" in s:
            return "CAD"
        elif "CHF" in s:
            return "CHF"
        return "OTHER"

    def connect(self, target_account: Optional[int] = None) -> bool:
        if not mt5.initialize(path=self.terminal_path, timeout=15000):
            logger.error(f"Cannot initialize MT5 at {self.terminal_path}: {mt5.last_error()}")
            return False

        # CRITICAL SECURITY & ROUTING: Ensure terminal is logged into the target account
        # (explicit target, else MT5_LOGIN env, else config/broker_config.json active_account).
        acc = ensure_account(mt5, target_account, logger=logger)
        if not acc:
            logger.critical("[FATAL SECURITY LOCK] Target MT5 account not active. ABORTING!")
            mt5.shutdown()
            return False

        # Pre-seed historical closed deals to prevent re-processing past sessions
        d_from = datetime.now() - timedelta(days=30)
        d_to = datetime.now() + timedelta(days=2)
        existing_deals = mt5.history_deals_get(d_from, d_to)
        if existing_deals:
            for d in existing_deals:
                self.processed_deal_tickets.add(d.ticket)
            logger.info(f"[+] Seeded {len(self.processed_deal_tickets)} historical closed deals into processed cache.")

        logger.info(f"[+] SAJIM V1 BOT CONNECTED: {acc.server} | Account: {acc.login} ({acc.name})")
        logger.info(f"[+] Balance: {acc.balance:.2f} {acc.currency} | Equity: {acc.equity:.2f} | Free Margin: {acc.margin_free:.2f} | Leverage: 1:{acc.leverage}")
        return True

    # =========================================================================
    # STAGE 4: SAJIM — Portfolio Filtering & Dynamic Position Sizing
    # =========================================================================
    def evaluate_signal_and_size(self, signal: BeepSignal) -> Optional[Dict[str, Any]]:
        """
        Evaluates an incoming BeepSignal against Sajim portfolio rules and computes dynamic lot sizing.
        """
        acc = mt5.account_info()
        if not acc:
            return None

        # 00. Global kill switch (KILL_SWITCH file in repo root or SAJIM_KILL_SWITCH=1)
        if not new_entries_allowed("V1"):
            return None

        # Cent detection strictly from the account currency (USC etc.), never the server name
        is_cent = is_cent_account(acc) or (getattr(self, "account_type", "") == "cent")
        unit_label = acc.currency or ("USC" if is_cent else "USD")

        # 0A. Daily Drawdown Circuit Breaker (UTC day, start-of-day equity baseline,
        #     floating P&L + commissions + swaps included via equity)
        today_deals = mt5.history_deals_get(utc_day_start(), utc_now() + timedelta(minutes=5)) or []
        self.daily_guard.max_dd_amount = from_major_units(self.max_daily_drawdown_usd, acc.currency)
        dd = self.daily_guard.evaluate(acc, today_deals)
        if not dd["ok"]:
            logger.warning(f"[🛑 DAILY CIRCUIT BREAKER ACTIVE] {dd['reason']}. New entries locked until 00:00 UTC.")
            return None

        # 0B. The Clean Plate Protocol: Reject blacklisted toxic assets immediately
        wl_mgr = get_whitelist_manager()
        if wl_mgr.is_toxic(signal.symbol, signal.timeframe):
            logger.warning(f"[🚫 DIRTY PLATE REJECTED] {signal.symbol} is blacklisted for whipsaw volatility / contract mismatch. Signal skipped.")
            return None

        # 0B1. Empirical Edge Matrix Filter: Only allow verified positive-expectancy pairs & timeframes
        from config.v1_edge_filter import is_v1_approved
        if not is_v1_approved(signal.symbol, signal.timeframe):
            logger.info(f"[🛡️ V1 EDGE FILTER] {signal.symbol} ({signal.timeframe}) is not in verified edge whitelist (Bleeder/Marginal). Skipped.")
            return None

        # 0B2. Coexistence Gatekeeper Pre-Entry Hook (if attached during dual co-execution)
        if getattr(self, "pre_entry_hook", None) is not None:
            cleared, reason = self.pre_entry_hook("V1", signal.symbol, signal.action)
            if not cleared:
                logger.info(f"[🛡️ COEXISTENCE GATE] V1 entry blocked on {signal.symbol}: {reason}")
                return None

        # 0C. Capital Milestone Standby Gate (Gold Preservation Shield)
        min_equity_usd = STANDBY_ASSETS_USD.get(wl_mgr._clean_symbol(signal.symbol), 0.0)
        equity_usd = to_major_units(acc.equity, acc.currency)
        if min_equity_usd > 0 and equity_usd < min_equity_usd:
            logger.info(
                f"[⏸️ GOLD STANDBY PROTOCOL] {signal.symbol} benched on STANDBY! "
                f"Current equity (${equity_usd:.2f} USD-equivalent) < required milestone (${min_equity_usd:.2f}). "
                f"Preventing 90% wick meat-grinder friction bleed. Ammunition 100% focused on clean Forex."
            )
            return None

        # 1. Margin Safeguard Check: Ensure sufficient free margin (> 5.0 USC on Cent, > 20.0 USD on Standard)
        min_free_margin = 5.0 if is_cent else 20.0
        if acc.margin_free < min_free_margin:
            logger.warning(f"[!] Margin Safeguard Active: Free Margin ({acc.margin_free:.2f} {unit_label}) < {min_free_margin:.1f} {unit_label}. Signal {signal.symbol} skipped.")
            return None

        # 2. Spread-to-Risk Efficiency Gate (\eta_plate <= 0.15)
        # Never trade assets where broker spread consumes > 15% of Stop Loss!
        sym_info = mt5.symbol_info(signal.symbol)
        if sym_info:
            spread_dist = sym_info.spread * sym_info.point
            sl_dist = abs(float(signal.entry_price) - float(signal.stop_loss))
            if sl_dist > 0:
                eta_plate = spread_dist / sl_dist
                if eta_plate > 0.15:
                    logger.warning(
                        f"[🚫 SPREAD GATE REJECTED] {signal.symbol}: Spread ({sym_info.spread} pts = {spread_dist:.5f}) "
                        f"consumes {eta_plate*100:.1f}% of Stop Loss (> 15% threshold). Trade skipped."
                    )
                    return None

            # 2A. SPREAD-TO-ATR EFFICIENCY GATE (ATR_M5 / Spread >= 3.0)
            # Rejects any asset where broker spread eats > 33% of the 5-minute candle range!
            rates_m5 = mt5.copy_rates_from_pos(signal.symbol, mt5.TIMEFRAME_M5, 0, 15)
            if rates_m5 is not None and len(rates_m5) >= 14:
                tr_vals = [
                    max(
                        rates_m5[i]['high'] - rates_m5[i]['low'],
                        abs(rates_m5[i]['high'] - rates_m5[i-1]['close']),
                        abs(rates_m5[i]['low'] - rates_m5[i-1]['close'])
                    )
                    for i in range(1, len(rates_m5))
                ]
                atr_m5_pts = (sum(tr_vals) / len(tr_vals)) / sym_info.point
                if sym_info.spread > 0 and (atr_m5_pts / sym_info.spread) < 3.0:
                    logger.warning(
                        f"[🚫 SPREAD-TO-ATR GATE REJECTED] {signal.symbol}: ATR ({atr_m5_pts:.1f} pts) / "
                        f"Spread ({sym_info.spread} pts) = {atr_m5_pts / sym_info.spread:.2f} < 3.0 (Spread eats >33% volatility). Trade skipped."
                    )
                    return None

        # 2.05 ZERO-CHOP RANGING BAN: Reject all ranging and boundary absorption setups!
        # Deploy strictly on high-conviction institutional trend expansions (DIAMOND & RARE only)
        if signal.layer in ("BOUNDARY_ABSORPTION", "RANGE_HARVEST"):
            return None

        if signal.layer not in ("DIAMOND", "RARE"):
            return None

        if abs(float(signal.m_t)) < 55.0:
            return None

        # 2.06 GOLD VELOCITY TIMEFRAME CONSTRAINT:
        # At $4,400 price level, H1/H4 stop distances ($18-$35) exceed our 3.0% equity shield on $365.
        # We trade Gold strictly on M5, M15, and M30 where stops are $7.00 - $10.00, ensuring
        # the trade has ample breathing room (> 1.2x M5 ATR) while capping total risk to ~$7 - $10 USD (1.9% - 2.7%).
        if "XAU" in signal.symbol and signal.timeframe in ("H1", "H4", "D1"):
            return None

        # 2.1 Chameleon Regime Classifier: Dynamic Exposure Cap
        kappa, regime_label = SajimChameleonClassifier.calculate_compression_ratio(
            symbol=signal.symbol,
            cur_price=float(signal.entry_price),
            m_t=float(signal.m_t)
        )
        regime_params = SajimChameleonClassifier.get_regime_params(regime_label)
        max_allowed_concurrency = min(self.max_positions, regime_params["max_concurrent_positions"])

        all_open_positions = mt5.positions_get() or []
        bot_positions = [p for p in all_open_positions if p.magic == MAGIC_V1]

        # High-Velocity VIP Priority (opt-in via vip_extra_slots; default 0 = no extra slots)
        is_high_velocity = wl_mgr._clean_symbol(signal.symbol) in ("XAUUSD", "GBPUSD", "EURUSD")
        effective_cap = max_allowed_concurrency + (self.vip_extra_slots if is_high_velocity else 0)

        if len(bot_positions) >= effective_cap:
            logger.info(
                f"[🔒 REGIME CONCURRENCY CAP] {signal.symbol} skipped: {len(bot_positions)} active positions "
                f">= max allowed {effective_cap} in {regime_label} ({regime_params['name']}). Zero friction drain."
            )
            return None

        # 3. Symbol Diversification Guard & Zero-Risk Pyramiding (\Psi)
        all_open_positions = mt5.positions_get() or []
        existing_positions = [p for p in all_open_positions if p.symbol == signal.symbol and p.magic == MAGIC_V1]
        is_scale_in = False
        if existing_positions:
            pos0 = existing_positions[0]
            is_buy = (pos0.type == 0)
            at_be = (pos0.sl >= pos0.price_open) if is_buy else (pos0.sl <= pos0.price_open)
            # Only 1 scale-in allowed per asset (max 2 positions total)
            is_risk_free = at_be or (pos0.ticket in self.harvested_tickets) or (pos0.ticket in self.partially_closed_tickets)
            if len(existing_positions) == 1 and is_risk_free:
                cur_health = self.beep_engine.evaluate_position_health(
                    symbol=pos0.symbol,
                    action="BUY" if is_buy else "SELL",
                    open_price=pos0.price_open,
                    sl=pos0.sl,
                    cur_price=pos0.price_current,
                    timeframe="M15",
                )
                if cur_health.get("health_score", 0.0) >= 0.70:
                    is_scale_in = True
                    logger.info(
                        f"[⚡ RISK-FREE HOUSE-MONEY PYRAMID] #{pos0.ticket} on {signal.symbol} is secured at BE/Harvest "
                        f"(H(t)={cur_health.get('health_score'):.2f}). Sizing 0.5x scale-in runner with ZERO balance risk!"
                    )
            if not is_scale_in:
                return None

        # 3b. Dealer State-Space & Gamma Tensor Gate (Institutional Market Microstructure)
        rates_m5 = mt5.copy_rates_from_pos(signal.symbol, mt5.TIMEFRAME_M5, 0, 15)
        rates_list = [r for r in rates_m5] if rates_m5 is not None else []
        sym_info = mt5.symbol_info(signal.symbol)
        spread_val = (sym_info.spread * sym_info.point) if sym_info else 0.0001
        point_val = sym_info.point if sym_info else 0.00001

        dealer_ok, dealer_boost, dealer_regime, dealer_narrative = self.dealer_engine.evaluate_dealer_alignment(
            symbol=signal.symbol,
            action=signal.action,
            cur_price=signal.entry_price,
            rates_m5=rates_list,
            spread=spread_val,
            point=point_val,
        )
        if not dealer_ok:
            logger.info(f"[🏛️ DEALER GATE REJECT] {signal.symbol} {signal.action} blocked: {dealer_narrative}")
            return None

        # 3c. 3-Candle Volume Absorption & Sub-Second Tick OFI Confirmation Gate
        # Synergizes macro 5-minute candle structure with micro atomic sub-second tape flow
        ticks_stream = None
        try:
            ticks_stream = mt5.copy_ticks_from(signal.symbol, datetime.now() - timedelta(seconds=60), 50, mt5.COPY_TICKS_ALL)
        except Exception as e:
            logger.debug(f"Tick fetch exception for {signal.symbol}: {e}")

        tc_ok, tc_boost, tc_narrative, tc_metrics = ThreeCandleTickConfirmationEngine.evaluate_three_candle_and_tick(
            symbol=signal.symbol,
            action=signal.action,
            rates_m5=rates_list,
            ticks=ticks_stream,
            min_wick_ratio=0.15,
        )
        if not tc_ok:
            logger.info(f"[🕯️ 3-CANDLE / TAPE REJECT] {signal.symbol} {signal.action} blocked: {tc_narrative}")
            return None

        logger.info(f"[🕯️ 3-CANDLE + TAPE CONFIRMED] {signal.symbol} {signal.action}: {tc_narrative}")

        # 4. Opportunist Correlation Derating (Equation 10: Delta(K) = 1/sqrt(K+1))
        # Never reject correlated pairs outright! Trade both fronts, derating risk dynamically.
        sym_clean = signal.symbol.replace(".c", "")
        base_curr = sym_clean[:3] if len(sym_clean) >= 6 else ""
        quote_curr = sym_clean[3:6] if len(sym_clean) >= 6 else ""
        cluster = self.get_cluster(signal.symbol)

        base_count = sum(1 for p in all_open_positions if base_curr and base_curr in p.symbol)
        quote_count = sum(1 for p in all_open_positions if quote_curr and quote_curr in p.symbol)
        cluster_count = max(base_count, quote_count)

        # Safeguard: Extreme ceiling only if single currency has 10+ concurrent trades
        if cluster_count >= 10:
            logger.info(f"[!] Currency saturation reached: {base_curr}/{quote_curr} already has {cluster_count} active trades. Signal skipped.")
            return None

        delta_k = 1.0 / math.sqrt(cluster_count + 1)

        # 5. Symbol Loss Cooldown Guard: Do not revenge-trade an asset that recently stopped out
        now = datetime.now()
        cooldown_expiry = self.symbol_cooldowns.get(signal.symbol)
        if cooldown_expiry and cooldown_expiry > now:
            # Check if this asset is on standby for an independent Hummingbird Re-Entry!
            if signal.symbol in self.pending_reentry_symbols:
                logger.info(f"[🎯 HUMMINGBIRD INDEPENDENT RE-ENTRY] {signal.symbol} authorized! Sizing on newly compounded balance.")
                self.pending_reentry_symbols.discard(signal.symbol)
            else:
                return None

        # 6. Dynamic Multi-Variable Stake Maximizer Omega (Equation 11) & Conviction Multiplier X_mult
        cluster_streak = self.cluster_streaks.get(cluster, 0)

        # Multi-Variable Factors: Free Margin ratio, Kinetic Mass, Conviction Phi
        fm_ratio = max(0.2, min(1.2, acc.margin_free / max(1.0, acc.equity)))
        m_ratio = max(0.5, min(1.8, abs(signal.m_t) / 55.0))
        phi_energy = getattr(signal, "phi_energy", 50.0)
        phi_ratio = max(0.5, min(1.8, phi_energy / 50.0))

        # Dynamic expansion rate per win in this cluster:
        kappa_dynamic = self.streak_rate * fm_ratio * m_ratio * phi_ratio
        streak_mult = (1.0 + kappa_dynamic) ** cluster_streak

        # Dynamic Conviction Multiplier X_mult
        x_mult = 1.0
        if abs(signal.m_t) >= 75.0:
            x_mult += 0.35  # Extreme institutional mass
        if phi_energy >= 65.0:
            x_mult += 0.25  # High conviction layer
        if fm_ratio >= 0.75:
            x_mult += 0.20  # Ample free margin

        x_mult *= dealer_boost * tc_boost  # Institutional dealer + 3-Candle tape alignment multiplier

        if is_scale_in:
            x_mult = 0.50  # Half-size runner while the first position is secured at BE/harvest

        # Scale risk: 1.5% base risk on forex, dynamically expanded up to 2.5-3.0% on Gold / High-Velocity diamond setups
        is_high_velocity = signal.symbol in ("XAUUSD", "GBPUSD", "XAUUSD.c", "GBPUSD.c")
        effective_base_risk = (self.base_risk * 1.5) if (is_high_velocity and (dealer_boost > 1.0 or tc_boost > 1.0)) else self.base_risk
        asset_risk_ceiling = 0.050 if is_cent else (0.030 if is_high_velocity else self.max_risk)

        # No risk FLOOR: derating (correlation, scale-in 0.5x) must be able to reduce risk.
        dynamic_risk = min(asset_risk_ceiling, effective_base_risk * streak_mult * delta_k * x_mult)

        lot, risk_cash, specs = UniversalLotCalculator.calculate_lot(
            symbol=signal.symbol,
            equity=acc.equity,
            risk_fraction=dynamic_risk,
            entry_price=signal.entry_price,
            stop_price=signal.stop_loss,
            account_currency=acc.currency,
        )
        if lot <= 0:
            logger.info(f"[🛡️ LOT REJECTED] {signal.symbol}: {specs.get('rejected', 'cannot size within risk budget')}. Trade skipped.")
            return None

        # Hard Risk Ceiling: Maximum 5.0% for Cent (allows 0.01 lot min sizing on 100 USC), 2.0% for Standard Forex
        actual_risk_cash = specs.get("actual_risk_cash", risk_cash)
        max_allowed_risk_cash = acc.equity * asset_risk_ceiling
        if actual_risk_cash > max_allowed_risk_cash:
            logger.warning(
                f"[🛡️ ACCOUNT SHIELD GUARD] {signal.symbol} min-lot risk ({actual_risk_cash:.2f} {unit_label}) "
                f"> max allowed ({max_allowed_risk_cash:.2f} {unit_label}, {asset_risk_ceiling*100:.1f}%). Trade rejected."
            )
            return None

        # 6. Margin-Cap Allocation Guard:
        # Micro-sizing for expansive data collection: Cap margin at 5% equity per position
        order_type = mt5.ORDER_TYPE_BUY if signal.action == "BUY" else mt5.ORDER_TYPE_SELL
        margin_req = mt5.order_calc_margin(order_type, signal.symbol, float(lot), float(signal.entry_price))
        sym_info = mt5.symbol_info(signal.symbol)
        if (not margin_req or margin_req <= 0) and sym_info:
            contract_size = sym_info.trade_contract_size or (1.0 if "XAU" in signal.symbol else 1000.0)
            leverage = max(1, acc.leverage)
            if signal.symbol.endswith(".c"):
                margin_req = (float(lot) * contract_size * 100.0) / leverage
            else:
                margin_req = (float(lot) * contract_size * float(signal.entry_price)) / leverage

        max_allowed_margin = min(acc.equity * 0.05, acc.margin_free * 0.15)

        sized_lot = lot
        if margin_req and margin_req > max_allowed_margin and max_allowed_margin > 0:
            scale_factor = max_allowed_margin / margin_req
            scaled = floor_volume(lot * scale_factor, sym_info) if sym_info else 0.0
            if scaled <= 0:
                logger.info(
                    f"[🛡️ MARGIN CAP] {signal.symbol}: even the minimum lot needs more margin than the "
                    f"cap ({max_allowed_margin:.2f} {unit_label}). Trade skipped."
                )
                return None
            lot = scaled
        # JPY Volatility Modulation: JPY pairs carry 110+ pts M5 ATR. Derate lot size by 40%
        if "JPY" in signal.symbol and sym_info:
            derated = floor_volume(lot * 0.60, sym_info)
            lot = derated if derated > 0 else min(lot, float(sym_info.volume_min or lot))
        if sized_lot > 0 and lot != sized_lot:
            risk_cash = risk_cash * (lot / sized_lot)

        return {
            "signal": signal,
            "lot": lot,
            "order_type": order_type,
            "dynamic_risk_pct": round(dynamic_risk * 100.0, 2),
            "risk_cash": round(risk_cash, 2),
            "specs": specs,
        }

    # =========================================================================
    # STAGE 5: ENTRY — MT5 Order Dispatch & Execution
    # =========================================================================
    def execute_entry(self, prepared: Dict[str, Any]) -> bool:
        """Dispatches the prepared deal to MT5 trade server with multi-filling mode fallback."""
        sig: BeepSignal = prepared["signal"]
        lot: float = prepared["lot"]
        order_type = prepared["order_type"]

        logger.info(f"\n>>> [PIPELINE: ENTRY DISPATCH -> {sig.symbol} ({sig.timeframe})]")
        logger.info(f"    Layer: {sig.layer} | M(t): {sig.m_t:+.2f} | Action: {sig.action} @ {sig.entry_price}")
        logger.info(f"    Sized: {lot} Lots (Risk: {prepared['dynamic_risk_pct']}% | Streak: {self.consecutive_wins})")
        logger.info(f"    SL: {sig.stop_loss} | TP: {sig.take_profit} (1:{sig.risk_reward} R:R)")

        if not new_entries_allowed("V1"):
            return False

        # Priced from a fresh tick at send time (ask for BUY / bid for SELL), with
        # requote retries and filling-mode fallback. Dry run sends nothing.
        ok, res, fill_price = send_market_order(
            symbol=sig.symbol,
            action=sig.action,
            volume=float(lot),
            sl=float(sig.stop_loss),
            tp=float(sig.take_profit),
            magic=MAGIC_V1,
            comment=f"Sajim_{sig.layer}",
            dry_run=self.dry_run,
            bot_name="V1",
        )
        if not ok:
            return False
        if self.dry_run:
            logger.info("    [SIMULATED DRY RUN] No order sent.")
            return True

        ticket = int(res.order)
        self.position_store.record_entry(ticket, sig.symbol, fill_price or float(sig.entry_price), float(sig.stop_loss), bot="V1")
        logger.info(f"[+] EXECUTED: Ticket #{ticket} on {sig.symbol} ({lot} Lots) @ {fill_price} | SL: {sig.stop_loss} | TP: {sig.take_profit}")
        self.total_trades_taken += 1
        try:
            self.bus.broadcast_trade_executed(
                ticket=ticket,
                symbol=sig.symbol,
                action=sig.action,
                lot=lot,
                entry=fill_price or sig.entry_price,
                sl=sig.stop_loss,
                tp=sig.take_profit,
                layer=sig.layer,
            )
        except Exception as b_err:
            logger.warning(f"Failed to broadcast trade execution: {b_err}")
        return True

    def check_hummingbird_exhaustion(self, pos, profit_r: float, cur_health: Dict[str, Any], sym_info) -> Tuple[bool, str]:
        """
        Evaluates whether an active winning position (profit_r >= 1.50R)
        has hit statistical momentum exhaustion and should be harvested at peak.
        """
        if profit_r < RC.V1_HUMMINGBIRD_MIN_R:
            return False, ""

        h_t = cur_health.get("health_score", 0.50)
        is_buy = (pos.type == mt5.ORDER_TYPE_BUY or pos.type == 0)

        # 1. Query M15 candle geometry for counter-wick rejection and Baseline B(t) distance
        rates = mt5.copy_rates_from_pos(pos.symbol, mt5.TIMEFRAME_M15, 0, 15)
        opp_wick = 0.0
        dist_b_t_atr = 0.0
        if rates is not None and len(rates) >= 2:
            last_bar = rates[-1]
            candle_range = max(sym_info.point * 10, last_bar['high'] - last_bar['low'])
            if is_buy:
                opp_wick = (last_bar['high'] - max(last_bar['open'], last_bar['close'])) / candle_range
            else:
                opp_wick = (min(last_bar['open'], last_bar['close']) - last_bar['low']) / candle_range

            # Calculate distance from Baseline B(t)
            closes = [r['close'] for r in rates]
            b_t = sum(closes) / len(closes)
            cur_p = pos.price_current
            dist_b_t = abs(cur_p - b_t)
            tr = max(last_bar['high'] - last_bar['low'], sym_info.point * 10)
            dist_b_t_atr = dist_b_t / tr if tr > 0 else 0.0

        # Vector A: Deep profit (>= +1.8R) AND counter-wick rejection >= 0.35 (Supply/Demand Wall)
        if profit_r >= RC.V1_HUMMINGBIRD_WICK_R and opp_wick >= 0.35:
            return True, f"Counter-Wick Rejection ({opp_wick*100:.1f}%) at +{profit_r:.2f}R"

        # Vector B: Profit is >= +1.5R AND Health H(t) collapsed below 0.65 from peak
        if profit_r >= RC.V1_HUMMINGBIRD_MIN_R and h_t < 0.65:
            return True, f"Momentum Health Rollover (H(t)={h_t:.2f} < 0.65) at +{profit_r:.2f}R"

        # Vector C: Severe Baseline Overextension (>= 2.2x ATR) with stall
        if profit_r >= RC.V1_HUMMINGBIRD_STRETCH_R and dist_b_t_atr >= 2.20 and opp_wick >= 0.25:
            return True, f"Baseline Envelope Stretch ({dist_b_t_atr:.1f}x ATR) at +{profit_r:.2f}R"

        return False, ""

    def _dry_run_once(self, ticket: int, action: str) -> bool:
        """In dry run, 'performs' a given action for a ticket only once (log de-duplication)."""
        key = (int(ticket), action)
        if key in self._dry_run_actions:
            return False
        self._dry_run_actions.add(key)
        return True

    def _close(self, pos, comment: str, volume: Optional[float] = None) -> bool:
        """Closes (part of) a position; in dry run only logs what would be sent."""
        if self.dry_run:
            if not self._dry_run_once(pos.ticket, comment):
                return False
            close_position(pos, magic=MAGIC_V1, comment=comment, dry_run=True, volume=volume, bot_name="V1")
            if volume is None or volume >= pos.volume:
                self.dry_run_closed.add(pos.ticket)
            return True
        return close_position(pos, magic=MAGIC_V1, comment=comment, dry_run=False, volume=volume, bot_name="V1")

    def _modify_sl(self, pos, new_sl: float, tp: float, tag: str, digits: int) -> bool:
        """Moves the SL; failures are logged by modify_sltp. Dry run only logs (once per stage)."""
        if self.dry_run and not self._dry_run_once(pos.ticket, tag):
            return False
        return modify_sltp(pos, new_sl, tp, dry_run=self.dry_run, bot_name="V1", digits=digits)

    def _broadcast(self, fn_name: str, *args, **kwargs) -> None:
        """Telegram/bus broadcasts are suppressed in dry run (nothing really happened)."""
        if self.dry_run:
            return
        try:
            getattr(self.bus, fn_name)(*args, **kwargs)
        except Exception as b_err:
            logger.warning(f"Failed to broadcast {fn_name}: {b_err}")

    # =========================================================================
    # STAGE 6: MANAGEMENT — Continuous BEEP Health H(t), 50% Cash Milker & Ratchet
    # =========================================================================
    def manage_open_positions(self):
        """
        Monitors active positions with Continuous BEEP Trade Health H(t) & Two-Stage Ratchet.
        All R-multiples use the INITIAL risk recorded at entry (persisted in
        state/v1_positions.json); tickets whose initial risk cannot be recovered are
        skipped for R-based management (their broker SL/TP still protect them).
        In dry run nothing is sent to the broker.
          - Narrative Scratch: H(t) < 0.30 and -0.45R <= PnL <= -0.10R -> close early
          - 45-minute Stagnation exit
          - Hummingbird peak harvest
          - 50% Partial Cash Milker at +1.5R, remaining runner to BE + spread
          - Safe Break-Even at +2.0R, Lock +1.5R at +2.8R
        Thresholds: v2/risk/constants.py
        """
        positions = mt5.positions_get()
        if positions is None:
            return  # terminal disconnected: do NOT prune state

        bot_positions = [p for p in positions if p.magic == MAGIC_V1]
        self.position_store.prune([p.ticket for p in bot_positions])
        open_tickets = {p.ticket for p in bot_positions}
        self.harvested_tickets &= open_tickets
        self.dry_run_closed &= open_tickets

        for pos in bot_positions:
            if pos.ticket in self.dry_run_closed:
                continue

            sym_info = mt5.symbol_info(pos.symbol)
            if not sym_info:
                continue

            is_buy = (pos.type == mt5.ORDER_TYPE_BUY or pos.type == 0)
            action_str = "BUY" if is_buy else "SELL"
            spread_cost = sym_info.spread * sym_info.point

            tick = mt5.symbol_info_tick(pos.symbol)
            if tick:
                cur_p = tick.bid if is_buy else tick.ask
                tick_vol = getattr(tick, 'volume', 1.0) or 1.0
                try:
                    self.dealer_engine.ingest_tick(pos.symbol, tick.bid, tick.ask, tick_vol, spread_cost)
                except Exception:
                    pass
            else:
                cur_p = pos.price_current

            entry_p = pos.price_open
            sl = pos.sl
            tp = pos.tp

            risk = self.position_store.initial_risk(pos, mt5_module=mt5)
            if not risk or risk <= 0:
                if pos.ticket not in self._unknown_risk_warned:
                    self._unknown_risk_warned.add(pos.ticket)
                    logger.warning(
                        f"[V1] #{pos.ticket} {pos.symbol}: initial risk unknown (no entry record / order SL). "
                        f"R-based management skipped; broker SL/TP remain in force."
                    )
                continue
            profit_dist = (cur_p - entry_p) if is_buy else (entry_p - cur_p)
            profit_r = profit_dist / risk

            # Query Continuous Live BEEP Health H(t)
            health = self.beep_engine.evaluate_position_health(
                symbol=pos.symbol,
                action=action_str,
                open_price=entry_p,
                sl=sl,
                cur_price=cur_p,
                timeframe="M15",
            )
            h_t = health.get("health_score", 0.50)
            h_narrative = health.get("narrative", "")

            # -----------------------------------------------------------------
            # 1. STREAMING HEALTH EUTHANASIA (H(t) < 0.30)
            # -----------------------------------------------------------------
            if (h_t < RC.V1_SCRATCH_HEALTH and RC.V1_SCRATCH_MIN_R <= profit_r <= RC.V1_SCRATCH_MAX_R) or (
                h_t < RC.V1_SCRATCH_DEEP_HEALTH and profit_r < RC.V1_SCRATCH_MIN_R
            ):
                if self._close(pos, "Sajim_Scratch"):
                    logger.warning(
                        f"[⚡ NARRATIVE SCRATCH]{' [DRY RUN]' if self.dry_run else ''} Closed #{pos.ticket} on {pos.symbol} "
                        f"(H(t)={h_t:.2f} | PnL={profit_r:.2f}R)."
                    )
                    self.symbol_cooldowns[pos.symbol] = datetime.now() + timedelta(minutes=self.cooldown_minutes)
                    self._broadcast("broadcast_narrative_scratch", pos.ticket, pos.symbol, h_t, pos.profit, h_narrative)
                    continue

            # -----------------------------------------------------------------
            # 1b. 45-MINUTE STAGNATION EUTHANASIA (Free Dead Capital)
            # -----------------------------------------------------------------
            pos_open_time = getattr(pos, 'time', 0)
            now_ts = time.time()
            pos_age_min = (now_ts - pos_open_time) / 60.0 if pos_open_time > 0 else 0.0

            if (pos_age_min >= RC.V1_STAGNATION_MINUTES
                    and (RC.V1_STAGNATION_MIN_R <= profit_r <= RC.V1_STAGNATION_MAX_R)
                    and h_t < RC.V1_STAGNATION_HEALTH):
                if self._close(pos, "Sajim_Stagnation"):
                    logger.info(
                        f"[⏳ STAGNATION EUTHANASIA]{' [DRY RUN]' if self.dry_run else ''} Closed #{pos.ticket} on {pos.symbol} "
                        f"after {pos_age_min:.0f} mins (PnL={profit_r:.2f}R | H(t)={h_t:.2f})."
                    )
                    self.symbol_cooldowns[pos.symbol] = datetime.now() + timedelta(minutes=15)
                    self._broadcast(
                        "broadcast_narrative_scratch",
                        pos.ticket, pos.symbol, h_t, pos.profit, "45-min Stagnation Exit -- Capital Recycled",
                    )
                    continue

            # -----------------------------------------------------------------
            # 2. THE HUMMINGBIRD PEAK HARVEST (Full Nectar Extraction at Peak)
            # -----------------------------------------------------------------
            is_exhausted, exhaust_reason = self.check_hummingbird_exhaustion(pos, profit_r, health, sym_info)
            if is_exhausted:
                if self._close(pos, "Sajim_Hummingbird"):
                    logger.info(
                        f"[🦅 HUMMINGBIRD HARVEST]{' [DRY RUN]' if self.dry_run else ''} Closed #{pos.ticket} on {pos.symbol} at PEAK! "
                        f"PnL: {pos.profit:+.2f} (+{profit_r:.2f}R) | Reason: {exhaust_reason}"
                    )
                    if not self.dry_run:
                        self.pending_reentry_symbols.add(pos.symbol)
                    self._broadcast(
                        "broadcast_hummingbird_harvest",
                        ticket=pos.ticket,
                        symbol=pos.symbol,
                        profit=pos.profit,
                        r_multiple=profit_r,
                        reason=exhaust_reason,
                    )
                    continue

            # -----------------------------------------------------------------
            # 3. TRANCHE 1 HARVEST: 50% CASH-IN-HAND AT +1.5R (Pesa kwa Mikono)
            # -----------------------------------------------------------------
            already_harvested = pos.ticket in self.harvested_tickets or self.position_store.is_harvested(pos.ticket)
            if profit_r >= RC.V1_HARVEST_TRIGGER_R and not already_harvested:
                close_vol = floor_volume(pos.volume / 2.0, sym_info)
                if close_vol > 0 and close_vol < pos.volume:
                    if self._close(pos, "Sajim_Harvest_50", volume=close_vol):
                        self.harvested_tickets.add(pos.ticket)
                        if not self.dry_run:
                            self.position_store.mark_harvested(pos.ticket)
                        half_profit = pos.profit * (close_vol / pos.volume)
                        logger.info(
                            f"[💰 PESA KWA MIKONO]{' [DRY RUN]' if self.dry_run else ''} Banked {close_vol} of #{pos.ticket} "
                            f"({pos.symbol}): {half_profit:+.2f}. Remaining {pos.volume - close_vol:.2f} lots runner."
                        )
                        # Move SL of remaining volume to Break-Even + spread cost
                        new_sl = round(entry_p + spread_cost if is_buy else entry_p - spread_cost, sym_info.digits)
                        if self._modify_sl(pos, new_sl, tp, "HARVEST_BE", sym_info.digits):
                            self._broadcast(
                                "broadcast_partial_banked",
                                ticket=pos.ticket,
                                symbol=pos.symbol,
                                volume_closed=close_vol,
                                profit_banked=half_profit,
                                remaining_vol=round(pos.volume - close_vol, 2),
                                new_sl=new_sl,
                            )
                        elif not self.dry_run:
                            logger.error(f"[V1] #{pos.ticket}: partial banked but runner SL NOT moved to BE (see error above).")

            # -----------------------------------------------------------------
            # 4. SAFE BREAK-EVEN AT +2.0R (For min-lot positions or unharvested)
            # -----------------------------------------------------------------
            if profit_r >= RC.V1_BREAKEVEN_TRIGGER_R:
                needs_be = (sl < entry_p) if is_buy else (sl == 0 or sl > entry_p)
                if needs_be:
                    new_sl = round(entry_p + spread_cost if is_buy else entry_p - spread_cost, sym_info.digits)
                    if self._modify_sl(pos, new_sl, tp, "BREAK_EVEN", sym_info.digits):
                        logger.info(f"[🛡️ SAFE BREAK-EVEN @ +{RC.V1_BREAKEVEN_TRIGGER_R}R]{' [DRY RUN]' if self.dry_run else ''} #{pos.ticket} ({pos.symbol}) SL -> {new_sl}")
                        self._broadcast("broadcast_ratchet_update", pos.ticket, pos.symbol, "BREAK_EVEN", new_sl, "Break-Even (+2.0R)")

            # -----------------------------------------------------------------
            # 5. STAGE 2 TRAILING LOCK: Lock +1.5R Net Profit at +2.8R
            # -----------------------------------------------------------------
            if profit_r >= RC.V1_LOCK_TRIGGER_R:
                target_sl = round(entry_p + (risk * RC.V1_LOCK_R) if is_buy else entry_p - (risk * RC.V1_LOCK_R), sym_info.digits)
                should_update = (target_sl > sl) if is_buy else (sl == 0 or target_sl < sl)
                if should_update:
                    if self._modify_sl(pos, target_sl, tp, "PROFIT_LOCK", sym_info.digits):
                        logger.info(f"[💰 PROFIT LOCKED @ +{RC.V1_LOCK_TRIGGER_R}R]{' [DRY RUN]' if self.dry_run else ''} #{pos.ticket} ({pos.symbol}) SL -> {target_sl}")
                        self._broadcast("broadcast_ratchet_update", pos.ticket, pos.symbol, "PROFIT_LOCKED", target_sl, "+1.5R Net Locked")

    # =========================================================================
    # STAGE 7: PNL — Deal History Synchronizer & Formulaic Growth/Loss Control
    # =========================================================================
    def sync_pnl_and_streaks(self):
        """
        Synchronizes closed deals from MT5 history using ticket tracking:
          - Each deal ticket is processed exactly once
          - Streaks are updated once per FULLY CLOSED position (partial closes are
            accumulated and folded into the final outcome, never counted as wins)
          - P&L includes profit + swap + commission + fee
          - Win: streak increment; Loss: formulaic step-back + symbol cooldown; BE: preserved
        """
        now = datetime.now()
        # Prune expired cooldowns
        self.symbol_cooldowns = {s: exp for s, exp in self.symbol_cooldowns.items() if exp > now}

        d_from = datetime.now(timezone.utc) - timedelta(days=2)
        d_to = datetime.now(timezone.utc) + timedelta(days=2)
        deals = mt5.history_deals_get(d_from, d_to)
        if deals:
            new_deals = [
                d for d in deals
                if d.magic == MAGIC_V1 and d.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT)
                and d.ticket not in self.processed_deal_tickets
            ]
            if not new_deals:
                return
            open_positions = mt5.positions_get()
            if open_positions is None:
                return  # cannot tell partial from full closes while disconnected
            open_tickets = {p.ticket for p in open_positions}
            new_deals.sort(key=lambda d: d.time)

            by_position: Dict[int, List[Any]] = {}
            for d in new_deals:
                self.processed_deal_tickets.add(d.ticket)
                pnl = float(d.profit) + float(d.swap) + float(getattr(d, "commission", 0.0) or 0.0) + float(getattr(d, "fee", 0.0) or 0.0)
                self.session_pnl += pnl
                pid = int(getattr(d, "position_id", 0) or d.ticket)
                by_position.setdefault(pid, []).append((d, pnl))

            for pid, items in by_position.items():
                chunk = sum(p for _, p in items)
                if pid in open_tickets:
                    # Partial close: position still running -> do not touch streaks yet
                    self._partial_pnl[pid] = self._partial_pnl.get(pid, 0.0) + chunk
                    continue
                profit = chunk + self._partial_pnl.pop(pid, 0.0)
                d = items[-1][0]
                cluster = self.get_cluster(d.symbol)
                cluster_streak = self.cluster_streaks.get(cluster, 0)

                if profit > 0.05:
                    self.consecutive_wins += 1
                    self.cluster_streaks[cluster] = cluster_streak + 1
                    logger.info(
                        f"[+] WIN DETECTED: Position #{pid} on {d.symbol} ({profit:+.2f}) | "
                        f"Cluster '{cluster}' Streak: {self.cluster_streaks[cluster]} | Global: {self.consecutive_wins}"
                    )
                    self._broadcast("broadcast_deal_closed", d.ticket, d.symbol, "WIN", profit, self.consecutive_wins, d.comment or "TP Hit")
                elif profit < -0.05:
                    old_global = self.consecutive_wins
                    old_cluster = cluster_streak
                    self.consecutive_wins = max(0, self.consecutive_wins - 1)
                    self.cluster_streaks[cluster] = max(0, cluster_streak - 1)
                    self.symbol_cooldowns[d.symbol] = now + timedelta(minutes=self.cooldown_minutes)
                    logger.info(
                        f"[-] LOSS DETECTED: Position #{pid} on {d.symbol} ({profit:+.2f}) | "
                        f"Cluster '{cluster}' Step-Back: {old_cluster} -> {self.cluster_streaks[cluster]} | "
                        f"Global: {old_global} -> {self.consecutive_wins} | Cooldown {self.cooldown_minutes}m activated"
                    )
                    self._broadcast("broadcast_deal_closed", d.ticket, d.symbol, "LOSS", profit, self.consecutive_wins, d.comment or "SL Hit")
                else:
                    logger.info(f"[🛡️ BE EXIT]: Position #{pid} on {d.symbol} Break-Even closed. Streaks preserved at Cluster: {cluster_streak}, Global: {self.consecutive_wins}")
                    self._broadcast("broadcast_deal_closed", d.ticket, d.symbol, "BE", profit, self.consecutive_wins, d.comment or "BE Close")
