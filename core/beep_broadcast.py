"""
========================================================================================
            SAJIM HOLDINGS — BEEP BROADCAST & COMMUNICATION BUS
                           (core/beep_broadcast.py)
========================================================================================
Chief Architect: Jimmy Mathu
CTO / Consumer: Tete (Signal Broadcast & Community Channels)

Mission:
  The central nervous system of Sajim Holdings.
  Captures all live quant events from the trading daemon and dispatches formatted,
  institutional narrative cards for WhatsApp VIP, Telegram channels, and student groups:
    1. SIGNAL BROADCASTS     : New DIAMOND / RARE institutional setups with context.
    2. TRADE ACTIVATIONS     : Real-time execution notifications with tickets.
    3. RATCHET UPDATES       : Stage 1 (Break-Even) & Stage 2 (Profit Lock) alerts.
    4. PNL & CLOSING CARDS   : Take Profit hits (+3.5R) and risk-controlled SL hits.
    5. SESSION NARRATIVE     : Asian, London, and NY institutional context cards.
========================================================================================
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

logger = logging.getLogger("BeepBroadcast")

# Persistence paths
BROADCAST_LOG = os.path.join(ROOT_DIR, "broadcast_stream.jsonl")
BROADCAST_ACTIVE_JSON = os.path.join(ROOT_DIR, "broadcast_active.json")


class BeepBroadcastBus:
    """
    Decoupled Event Broadcaster for Sajim Holdings.
    Thread-safe, append-only, and accessible via REST API or direct file streaming.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BeepBroadcastBus, cls).__new__(cls)
            cls._instance._init_bus()
        return cls._instance

    def _init_bus(self):
        self.recent_events: List[Dict[str, Any]] = []
        self._load_recent()

    def _load_recent(self):
        if os.path.exists(BROADCAST_ACTIVE_JSON):
            try:
                with open(BROADCAST_ACTIVE_JSON, "r", encoding="utf-8") as f:
                    self.recent_events = json.load(f)
            except Exception:
                self.recent_events = []

    def _save_event(self, event: Dict[str, Any]):
        """Persists event to both active cache and append-only stream."""
        self.recent_events.append(event)
        if len(self.recent_events) > 100:
            self.recent_events = self.recent_events[-100:]

        # 1. Update active JSON for fast API reads
        try:
            with open(BROADCAST_ACTIVE_JSON, "w", encoding="utf-8") as f:
                json.dump(self.recent_events, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to update {BROADCAST_ACTIVE_JSON}: {e}")

        # 2. Append to JSONL stream
        try:
            with open(BROADCAST_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.warning(f"Failed to append to {BROADCAST_LOG}: {e}")

        # 3. Real-Time Non-Blocking Telegram Channel Dispatch
        if "broadcast_text" in event:
            try:
                from core.telegram_broadcaster import send_telegram_card
                # Real executed trades, ratchets, profit proof, and scratches dispatch to 'all' (@sajimtraders)
                # Raw scanner-only signals stay in VIP
                target = "all" if event.get("type") in (
                    "TRADE_EXECUTED",
                    "V2_TRADE_EXECUTED",
                    "SIGNAL_GENERATED",
                    "V2_SIGNAL_GENERATED",
                    "DEAL_WIN",
                    "DEAL_LOSS",
                    "DEAL_BE",
                    "RATCHET_BREAK_EVEN",
                    "RATCHET_PROFIT_LOCKED",
                    "NARRATIVE_SCRATCH",
                    "TRADE_OPT_OUT",
                    "MARKET_REGIME_ADVISORY",
                    "DAILY_MARKET_DIGEST",
                    "CASH_MILK_PARTIAL",
                    "HUMMINGBIRD_HARVEST",
                ) else "all"
                send_telegram_card(event["broadcast_text"], parse_mode="HTML", target=target)
            except Exception as tg_err:
                logger.debug(f"Telegram dispatch deferred: {tg_err}")

    # =========================================================================
    # EVENT 1: SIGNAL DISPATCH (New Verified Setup)
    # =========================================================================
    def broadcast_signal(
        self,
        symbol: str,
        timeframe: str,
        action: str,
        layer: str,
        m_t: float,
        entry: float,
        sl: float,
        tp: float,
        rr: float,
        session: str = "LIVE_MARKET",
        why: str = "",
    ):
        clean_layer = str(layer).replace("_", " ")
        card = (
            f"🏛️ <b>Signal: {symbol} ({timeframe})</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Action: <b>{action}</b> @ <code>{entry}</code>\n"
            f"• Invalidation Floor (SL): <code>{sl}</code>\n"
            f"• Target Profit (TP): <code>{tp}</code> (1:{rr:.1f} R:R)\n"
            f"• Layer: {clean_layer}\n"
            f"• Edge M(t): <code>{m_t:+.2f}</code>"
        )
        event = {
            "id": f"SIG_{int(datetime.now().timestamp()*1000)}",
            "type": "SIGNAL_GENERATED",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "timeframe": timeframe,
            "action": action,
            "layer": layer,
            "m_t": m_t,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "rr": rr,
            "broadcast_text": card,
        }
        self._save_event(event)
        logger.info(f"[📢 BROADCAST] Signal published for {symbol} ({layer} {action})")
        return event

    # =========================================================================
    # EVENT 2: TRADE ACTIVATION (Execution on Broker)
    # =========================================================================
    def broadcast_trade_executed(
        self,
        ticket: int,
        symbol: str,
        action: str,
        lot: float,
        entry: float,
        sl: float,
        tp: float,
        layer: str,
    ):
        clean_layer = str(layer).replace("_", " ")
        card = (
            f"🏛️ <b>Sajim Institutional Signal: {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🧭 <b>Direction:</b> <b>{action}</b> @ <code>{entry}</code>\n"
            f"🛑 <b>Stop Loss:</b> <code>{sl}</code>\n"
            f"🎯 <b>Take Profit:</b> <code>{tp}</code>\n"
            f"💎 <b>Regime:</b> Institutional Trend Expansion\n"
            f"🛡️ <b>Risk:</b> Strictly 1.5% equity. Hold to target.\n"
            f"📌 <b>Management Directive:</b> Move SL to Break-Even at +1.5R. If you receive an Opt-Out alert, exit immediately at market!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Execution confirmed live via Sajim Quant Labs.</i>"
        )
        event = {
            "id": f"EXEC_{ticket}",
            "type": "TRADE_EXECUTED",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticket": ticket,
            "symbol": symbol,
            "action": action,
            "lot": lot,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "broadcast_text": card,
        }
        self._save_event(event)
        logger.info(f"[📢 BROADCAST] Trade activation published for #{ticket} ({symbol})")
        return event

    # =========================================================================
    # EVENT 1B: SAJIM V2 TREND DURATION SIGNAL DISPATCH
    # =========================================================================
    def broadcast_v2_signal(
        self,
        symbol: str,
        timeframe: str,
        action: str,
        strategy_name: str,
        entry: float,
        sl: float,
        tp: float,
        rr: float,
        trend_count: int,
        probable_length: float,
        maturity_ratio: float,
        phase: str,
        hma_val: float,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        mat = metadata or {}
        action_emoji = "🟢 BUY" if action == "BUY" else "🔴 SELL"
        phase_emoji = "🌱" if "EARLY" in phase.upper() else ("🔥" if "LATE" in phase.upper() else "⚖️")
        scalp_tag = "⚡ <b>[SCALPING OPPORTUNITY]</b> ⚡\n" if timeframe == "M1" else ""
        
        if strategy_name == "MirageLiquiditySweep":
            score = mat.get("score", 0.0)
            swept_lvl = mat.get("swept_level", 0.0)
            extreme = mat.get("wick_extreme", 0.0)
            is_choch = mat.get("is_choch", True)
            is_eq = mat.get("is_equal", False)
            choch_str = "✅ CHoCH Confirmed" if is_choch else "⚡ Raw Liquidity Sweep"
            eq_tag = " [EQH/EQL Magnet]" if is_eq else ""
            card = (
                f"💧 <b>[SAJIM V2] MIRAGE LIQUIDITY SWEEP: {symbol} ({timeframe})</b>\n"
                f"{scalp_tag}━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <b>Engine:</b> Mirage Liquidity Sweep Pro v1.3.1 (SMC)\n"
                f"⚡ <b>Sweep Quality Score:</b> <b>{score:.1f} / 100</b>\n"
                f"🧭 <b>Action:</b> <b>{action_emoji}</b> @ <code>{entry}</code>\n"
                f"🛑 <b>Stop Loss:</b> <code>{sl}</code>\n"
                f"🎯 <b>Take Profit:</b> <code>{tp}</code> (1:{rr:.1f} R:R Target)\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🌊 <b>Smart Money Telemetry:</b>\n"
                f"• Swept Liquidity Pool: <code>{swept_lvl:.5f}</code>{eq_tag}\n"
                f"• Sweep Wick Extreme: <code>{extreme:.5f}</code>\n"
                f"• Structure Shift (CHoCH): <b>{choch_str}</b>\n"
                f"• Break-Even Protocol: <b>Active Upon TP1 Touch</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<i>{reason}</i>"
            )
        else:
            card = (
                f"📊 <b>[SAJIM V2] TREND DURATION SIGNAL: {symbol} ({timeframe})</b>\n"
                f"{scalp_tag}━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <b>Engine:</b> Trend Duration Forecast (HMA-50)\n"
                f"⚡ <b>Strategy:</b> {strategy_name}\n"
                f"🧭 <b>Action:</b> <b>{action_emoji}</b> @ <code>{entry}</code>\n"
                f"🛑 <b>Stop Loss:</b> <code>{sl}</code>\n"
                f"🎯 <b>Take Profit:</b> <code>{tp}</code> (1:{rr:.1f} R:R Target)\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏳ <b>Trend Duration Telemetry:</b>\n"
                f"• Current Trend Count: <b>Bar {trend_count}</b>\n"
                f"• Probable Life Expectancy: <b>{probable_length:.1f} Bars</b>\n"
                f"• Statistical Maturity: <b>{maturity_ratio*100:.0f}%</b>\n"
                f"• Lifecycle Phase: {phase_emoji} <b>{phase}</b>\n"
                f"• HMA-50 Dynamic Baseline: <code>{hma_val:.5f}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<i>{reason}</i>"
            )
        event = {
            "id": f"SIG_V2_{int(datetime.now().timestamp()*1000)}",
            "type": "V2_SIGNAL_GENERATED",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bot_version": "V2",
            "symbol": symbol,
            "timeframe": timeframe,
            "action": action,
            "strategy": strategy_name,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "rr": rr,
            "trend_count": trend_count,
            "probable_length": probable_length,
            "maturity_ratio": maturity_ratio,
            "phase": phase,
            "hma_val": hma_val,
            "broadcast_text": card,
        }
        self._save_event(event)
        logger.info(f"[📢 V2 BROADCAST] Signal published for {symbol} ({strategy_name} {action}) | Phase: {phase}")
        return event

    # =========================================================================
    # EVENT 2B: SAJIM V2 TRADE ACTIVATION (Execution on Broker)
    # =========================================================================
    def broadcast_v2_trade_executed(
        self,
        ticket: int,
        symbol: str,
        action: str,
        lot: float,
        entry: float,
        sl: float,
        tp: float,
        strategy_name: str,
        maturity_info: Optional[Dict[str, Any]] = None,
        timeframe: str = "",
    ):
        mat = maturity_info or {}
        trend_count = mat.get("trend_count", 0)
        prob_len = mat.get("probable_length", 20.0)
        phase = mat.get("phase", "UNKNOWN")
        mat_pct = int(mat.get("maturity_ratio", 0.0) * 100)

        scalp_tag = "⚡ <b>[SCALPING OPPORTUNITY]</b> ⚡\n" if timeframe == "M1" else ""

        if strategy_name == "MirageLiquiditySweep":
            score = mat.get("score", 0.0)
            swept_lvl = mat.get("swept_level", 0.0)
            is_choch = mat.get("is_choch", True)
            choch_str = "CHoCH Confirmed" if is_choch else "Raw Sweep"
            card = (
                f"🚀 <b>[SAJIM V2 LIVE EXECUTION] #{ticket} {symbol}</b>\n"
                f"{scalp_tag}━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <b>Engine:</b> Mirage Liquidity Sweep Pro v1.3.1 (Magic 888222)\n"
                f"⚡ <b>Execution Mode:</b> {choch_str} (Score: {score:.1f}/100)\n"
                f"🧭 <b>Direction:</b> <b>{action}</b> {lot} Lots @ <code>{entry}</code>\n"
                f"🛑 <b>Stop Loss:</b> <code>{sl}</code>\n"
                f"🎯 <b>Take Profit:</b> <code>{tp}</code>\n"
                f"💧 <b>Swept Pool:</b> <code>{swept_lvl:.5f}</code>\n"
                f"🛡️ <b>Management:</b> Break-Even after TP1 (1R secured)\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<i>Execution confirmed live via Sajim Quant Labs V2 Engine.</i>"
            )
        else:
            card = (
                f"🚀 <b>[SAJIM V2 LIVE EXECUTION] #{ticket} {symbol}</b>\n"
                f"{scalp_tag}━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <b>Engine:</b> Sajim V2 Trend Duration Maturity (Magic 888222)\n"
                f"⚡ <b>Strategy Cartridge:</b> {strategy_name}\n"
                f"🧭 <b>Direction:</b> <b>{action}</b> {lot} Lots @ <code>{entry}</code>\n"
                f"🛑 <b>Stop Loss:</b> <code>{sl}</code>\n"
                f"🎯 <b>Take Profit:</b> <code>{tp}</code>\n"
                f"⏳ <b>Duration Maturity:</b> Bar {trend_count} / {prob_len:.0f} ({mat_pct}% - {phase})\n"
                f"🛡️ <b>Management Protocol:</b> Two-Stage Ratchet (+1.5R BE+0.15R | +2.2R Lock +1.0R)\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<i>Execution confirmed live via Sajim Quant Labs V2 Engine.</i>"
            )
        event = {
            "id": f"EXEC_V2_{ticket}",
            "type": "V2_TRADE_EXECUTED",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bot_version": "V2",
            "ticket": ticket,
            "symbol": symbol,
            "action": action,
            "lot": lot,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "strategy": strategy_name,
            "broadcast_text": card,
        }
        self._save_event(event)
        logger.info(f"[📢 V2 BROADCAST] Trade activation published for #{ticket} ({symbol})")
        return event

    # =========================================================================
    # EVENT 3: RATCHET MANAGEMENT (BE & Profit Lock)
    # =========================================================================
    def broadcast_ratchet_update(
        self,
        ticket: int,
        symbol: str,
        stage: str,  # "BREAK_EVEN" or "PROFIT_LOCKED"
        new_sl: float,
        r_level: str,
    ):
        if stage == "BREAK_EVEN":
            icon = "🛡️"
            title = "Trade Protected -> Break-Even"
            desc = "Trade reached +2.0R expansion. Stop Loss moved to Entry. Risk completely eliminated."
        else:
            icon = "💰"
            title = "Profit Locked (+1.5R Net)"
            desc = "Trade reached +2.8R expansion. Trailing Stop locked in solid profit."

        card = (
            f"{icon} <b>Sajim Trade Update: {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Action: <b>{title}</b>\n"
            f"• Protected SL: <code>{new_sl}</code>\n"
            f"• Status: {desc}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Sajim Institutional Risk Management</i>"
        )
        event = {
            "id": f"RATCHET_{ticket}_{int(datetime.now().timestamp())}",
            "type": f"RATCHET_{stage}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticket": ticket,
            "symbol": symbol,
            "stage": stage,
            "new_sl": new_sl,
            "r_level": r_level,
            "broadcast_text": card,
        }
        self._save_event(event)
        logger.info(f"[📢 BROADCAST] Ratchet update published for #{ticket} ({symbol} {stage})")
        return event

    # =========================================================================
    # EVENT 3B: PARTIAL CASH BANKED (50% Milk at +1.5R)
    # =========================================================================
    def broadcast_partial_banked(
        self,
        ticket: int,
        symbol: str,
        volume_closed: float,
        profit_banked: float,
        remaining_vol: float,
        new_sl: float,
    ):
        card = (
            f"💰 <b>Profit Secured: {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Realized Profit: <code>+${profit_banked:.2f} USD</code>\n"
            f"• Protected SL: <code>{new_sl}</code>\n"
            f"• Runner Volume: <code>{remaining_vol}</code> remaining to target\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Sajim Quant Labs</i>"
        )
        event = {
            "id": f"PARTIAL_{ticket}_{int(datetime.now().timestamp())}",
            "type": "CASH_MILK_PARTIAL",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticket": ticket,
            "symbol": symbol,
            "volume_closed": volume_closed,
            "profit_banked": profit_banked,
            "remaining_vol": remaining_vol,
            "new_sl": new_sl,
            "broadcast_text": card,
        }
        self._save_event(event)
        logger.info(f"[📢 BROADCAST] Cash milked published for #{ticket} ({symbol} +${profit_banked:.2f})")
        return event

    # =========================================================================
    # EVENT 3B-2: THE HUMMINGBIRD PEAK HARVEST (Full Profit Extraction at Peak)
    # =========================================================================
    def broadcast_hummingbird_harvest(
        self,
        ticket: int,
        symbol: str,
        profit: float,
        r_multiple: float,
        reason: str = "Momentum Exhaustion Peak",
    ):
        card = (
            f"🦅 <b>Sajim Hummingbird Harvest: {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Peak Profit Banked: <code>+${profit:.2f} USD</code> (+{r_multiple:.2f}R)\n"
            f"• Position: <code>#{ticket}</code> (100% Closed at Peak)\n"
            f"• Reason: {reason}\n"
            f"• Strategy: Capital secured in balance. Standing by for discounted baseline re-entry.\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Sajim Institutional Alpha Engine</i>"
        )
        event = {
            "id": f"HUMMING_{ticket}_{int(datetime.now().timestamp())}",
            "type": "HUMMINGBIRD_HARVEST",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticket": ticket,
            "symbol": symbol,
            "profit": profit,
            "r_multiple": r_multiple,
            "reason": reason,
            "broadcast_text": card,
        }
        self._save_event(event)
        logger.info(f"[🦅 BROADCAST] Hummingbird harvest published for #{ticket} ({symbol} +${profit:.2f} | +{r_multiple:.2f}R)")
        return event

    # =========================================================================
    # EVENT 3C: CLIENT OPT-OUT DIRECTIVE & NARRATIVE SCRATCH (Euthanasia at H(t) < 0.30)
    # =========================================================================
    def broadcast_narrative_scratch(
        self,
        ticket: int,
        symbol: str,
        h_t: float,
        pnl: float,
        narrative: str,
    ):
        card = (
            f"🚨 <b>TRADE ADVISORY: OPT-OUT / CLOSE NOW</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Asset:</b> <b>{symbol}</b> (Ticket #{ticket})\n"
            f"• <b>Action Directive:</b> <b>CLOSE AT MARKET OR MOVE SL TO BREAK-EVEN NOW!</b>\n"
            f"• <b>Quant Health:</b> <code>H(t) = {h_t:.2f} &lt; 0.30</code> (Momentum Dead)\n"
            f"• <b>Current State:</b> <code>-${abs(pnl):.2f} USD</code> | Early Euthanasia\n"
            f"• <b>Rationale:</b> {narrative}\n"
            f"• <b>Guidance:</b> Institutional order flow has dried up. Exit now to preserve capital and avoid taking a full Stop Loss hit!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Sajim Real-Time Client Protection Protocol</i>"
        )
        event = {
            "id": f"SCRATCH_{ticket}_{int(datetime.now().timestamp())}",
            "type": "NARRATIVE_SCRATCH",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticket": ticket,
            "symbol": symbol,
            "h_t": h_t,
            "pnl": pnl,
            "narrative": narrative,
            "broadcast_text": card,
        }
        self._save_event(event)
        logger.info(f"[🚨 BROADCAST] Client Opt-Out Advisory published for #{ticket} ({symbol} H(t)={h_t:.2f})")
        return event

    # =========================================================================
    # EVENT 3D: MARKET REGIME & PAIR AVOIDANCE ADVISORY
    # =========================================================================
    def broadcast_market_regime_advisory(
        self,
        symbol: str,
        status: str,  # "AVOID / RECESSION CHOP", "CAUTION / TIGHT STOPS", "STANDBY"
        reason: str,
        directive: str,
        safe_focus: str = "EURUSD, EURCAD, AUDUSD, USDCAD",
    ):
        card = (
            f"⚠️ <b>MARKET REGIME ADVISORY: {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Status:</b> 🛑 <b>{status}</b>\n"
            f"• <b>Market Condition:</b> {reason}\n"
            f"• <b>Client Directive:</b> {directive}\n"
            f"• <b>Recommended Safe Assets:</b> {safe_focus}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Sajim Quantitative Risk Advisory — Capital Preservation First</i>"
        )
        event = {
            "id": f"ADVISORY_{symbol}_{int(datetime.now().timestamp())}",
            "type": "MARKET_REGIME_ADVISORY",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "status": status,
            "reason": reason,
            "directive": directive,
            "broadcast_text": card,
        }
        self._save_event(event)
        logger.info(f"[⚠️ BROADCAST] Market advisory published for {symbol} ({status})")
        return event

    # =========================================================================
    # EVENT 3E: DAILY MARKET & PAIR HEALTH DIGEST
    # =========================================================================
    def broadcast_daily_market_digest(
        self,
        green_pairs: List[str],
        yellow_pairs: List[str],
        red_pairs: List[str],
        commentary: str,
    ):
        green_str = ", ".join(green_pairs) if green_pairs else "None"
        yellow_str = ", ".join(yellow_pairs) if yellow_pairs else "None"
        red_str = ", ".join(red_pairs) if red_pairs else "None"

        card = (
            f"📋 <b>SAJIM DAILY MARKET &amp; PAIR HEALTH DIGEST</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 <b>GREEN LIGHT (High Probability Trend Flow):</b>\n"
            f"   • <b>{green_str}</b>\n"
            f"   <i>Clean expansions, low spread friction, high-probability runners.</i>\n\n"
            f"🟡 <b>YELLOW LIGHT (Trade with Caution / Strict Retest):</b>\n"
            f"   • <b>{yellow_str}</b>\n"
            f"   <i>Elevated volatility, require confirmed 3-candle retest.</i>\n\n"
            f"🔴 <b>RED LIGHT / AVOID (Meat Grinder / Severe Friction):</b>\n"
            f"   • <b>{red_str}</b>\n"
            f"   <i>Heavy wick consolidation / toxic spread friction. Avoid manual trades!</i>\n\n"
            f"💡 <b>Quant Briefing:</b>\n"
            f"{commentary}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Sajim Holdings — Discipline Over FOMO</i>"
        )
        event = {
            "id": f"DIGEST_{int(datetime.now().timestamp())}",
            "type": "DAILY_MARKET_DIGEST",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "green": green_pairs,
            "yellow": yellow_pairs,
            "red": red_pairs,
            "broadcast_text": card,
        }
        self._save_event(event)
        logger.info("[📋 BROADCAST] Daily Market Digest published to channels.")
        return event

    # =========================================================================
    # EVENT 4: DEAL CLOSED (TP Smashed or Controlled Loss)
    # =========================================================================
    def broadcast_deal_closed(
        self,
        deal_ticket: int,
        symbol: str,
        result: str,  # "WIN" or "LOSS" or "BE"
        profit: float,
        streak: int,
        reason: str = "",
    ):
        if result == "WIN":
            card = (
                f"✅ <b>Take Profit Reached: {symbol}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• Target Profit Banked: <code>+${profit:.2f} USD</code>\n"
                f"• Institutional run completed successfully.\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<i>Sajim Quant Labs</i>"
            )
        elif result == "LOSS":
            card = (
                f"🛑 <b>Trade Closed: {symbol}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• Controlled Risk: <code>-${abs(profit):.2f} USD</code>\n"
                f"• Status: Structural invalidation reached. Capital protected strictly within risk limits.\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<i>Sajim Quant Labs</i>"
            )
        else:
            card = (
                f"⚖️ <b>Break-Even Exit: {symbol}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• Net PnL: <code>+${profit:.2f} USD</code>\n"
                f"• Status: Position closed risk-free after protecting capital.\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<i>Sajim Quant Labs</i>"
            )

        event = {
            "id": f"DEAL_{deal_ticket}",
            "type": f"DEAL_{result}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "deal_ticket": deal_ticket,
            "symbol": symbol,
            "result": result,
            "profit": profit,
            "streak": streak,
            "reason": reason,
            "broadcast_text": card,
        }
        self._save_event(event)
        logger.info(f"[📢 BROADCAST] Deal result published for #{deal_ticket} ({symbol} {result} {profit:+.2f})")
        return event

    # =========================================================================
    # EVENT 5: V2 QUANT EXPECTANCY REPORT
    # =========================================================================
    def broadcast_expectancy_report(self, stats: Dict[str, Any]):
        if "error" in stats:
            return None
        
        card = (
            f"📊 <b>[SAJIM QUANT EDGE] V2 Performance Matrix</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 <b>Total Scored Trades:</b> {stats['total_trades']}\n"
            f"✅ <b>Hits (Wins):</b> {stats['hits']} ({stats['win_rate']:.1f}%)\n"
            f"❌ <b>Misses (Losses):</b> {stats['misses']}\n"
            f"💰 <b>Average Output (Win):</b> <code>+${stats['avg_win']:.2f}</code>\n"
            f"🛡️ <b>Average Risk (Loss):</b> <code>-${stats['avg_loss']:.2f}</code>\n"
            f"📈 <b>Net Expectancy (EV):</b> <b>${stats['net_ev']:+.2f} USD</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Status: {stats['status']}"
        )
        
        event = {
            "id": f"EV_{int(datetime.now().timestamp())}",
            "type": "EXPECTANCY_REPORT",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "broadcast_text": card,
        }
        self._save_event(event)
        logger.info(f"[📊 BROADCAST] EV Report published: EV = ${stats['net_ev']:+.2f}")
        return event

    def get_pending_broadcasts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent broadcast events for Tete's API client."""
        return self.recent_events[-limit:]
