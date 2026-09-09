"""
========================================================================================
         SAJIM HOLDINGS — COMMUNITY CONCIERGE & CONVERSION AI
                   (core/sajim_community_concierge.py)
========================================================================================
Chief Architect: Jimmy Mathu

Mission:
  1. Manages Telegram community conversation 24/7 with zero manual effort from Jimmy.
  2. Welcomes new members into @sajimtraders with high-status, enticing onboarding.
  3. Provides live, verified MT5 account telemetry via interactive commands (/status).
  4. Educates members on BEEP Market Physics vs Sajim V1 Risk Architecture (/strategy).
  5. Answers common questions in English and Kenyan Sheng automatically.
  6. Drives conversions to VIP Elite (3,000 KES/mo) and FREE Broker Partner signups (/vip).
========================================================================================
"""

import os
import sys
import time
import json
import logging
import threading
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
CONFIG_FILE = os.path.join(ROOT_DIR, "config", "telegram_config.json")
STATUS_FILE = os.path.join(ROOT_DIR, "overnight_status.json")

logger = logging.getLogger("CommunityConcierge")


class SajimCommunityConcierge:
    """
    24/7 Autonomous Interactive Telegram Concierge & Conversion Bot.
    Operates non-blocking via background long-polling.
    """

    def __init__(self):
        self.bot_token: Optional[str] = None
        self.free_channel_id: Optional[str] = None
        self.vip_channel_id: Optional[str] = None
        self.broker_link: str = "https://headway.net/?ref=sajim_quant"
        self.admin_contact: str = "@sajim_admin"
        self.last_update_id: int = 0
        self.is_running: bool = False
        self.worker_thread: Optional[threading.Thread] = None

        self.load_config()

    def load_config(self):
        """Loads bot configuration from config/telegram_config.json."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.bot_token = data.get("bot_token")
                    self.free_channel_id = str(data.get("free_channel_id", ""))
                    self.vip_channel_id = str(data.get("vip_channel_id", ""))
                    self.broker_link = data.get("broker_partner_link", self.broker_link)
                    self.admin_contact = data.get("admin_contact", self.admin_contact)
            except Exception as e:
                logger.warning(f"Failed to read config: {e}")

    def get_live_status(self) -> Dict[str, Any]:
        """Reads real-time MT5 account metrics from overnight_status.json."""
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def send_message(self, chat_id: Any, text: str, parse_mode: str = "HTML") -> bool:
        """Sends a message to a specific chat/user via Telegram API."""
        if not self.bot_token:
            return False
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        try:
            data = urllib.parse.urlencode(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning(f"Failed to deliver message to {chat_id}: {e}")
            return False

    # =========================================================================
    # COMMAND HANDLERS
    # =========================================================================
    def handle_start(self, chat_id: Any, user_first_name: str = "Trader") -> str:
        return (
            f"👋 <b>Welcome {user_first_name} to Sajim Traders.</b>\n\n"
            f"We share our live algorithmic setups and market analysis here.\n\n"
            f"<b>Commands:</b>\n"
            f"• /status — Live MT5 account equity & balance\n"
            f"• /strategy — How our risk engine works\n"
            f"• /vip — VIP access details\n"
            f"• /broker — Recommended broker setup\n"
        )

    def handle_status(self) -> str:
        status = self.get_live_status()
        if not status:
            return "Syncing live MT5 feed... please try again in a few seconds."

        equity = status.get("equity", 0.0)
        balance = status.get("balance", 0.0)
        free_margin = status.get("free_margin", 0.0)
        positions = status.get("active_bot_positions", 0)

        open_pos = status.get("open_positions", [])
        milked = [p["symbol"] for p in open_pos if "Milk" in str(p.get("comment", ""))]
        milked_str = ", ".join(milked) if milked else "None at target yet"

        return (
            f"📊 <b>Live MT5 Status:</b>\n"
            f"• Equity: <code>${equity:.2f} USD</code>\n"
            f"• Balance: <code>${balance:.2f} USD</code>\n"
            f"• Free Margin: <code>${free_margin:.2f} USD</code>\n"
            f"• Open Positions: <code>{positions}</code>\n"
            f"• Protected Runners: <code>{milked_str}</code>"
        )

    def handle_strategy(self) -> str:
        return (
            f"🧠 <b>Sajim Risk & Execution Framework:</b>\n\n"
            f"1. <b>Anomaly Detection:</b> Identifies institutional liquidity sweeps and imbalances across 29 pairs.\n"
            f"2. <b>Spread Filter:</b> Never trades setups where the spread takes >15% of the stop loss.\n"
            f"3. <b>Dynamic Milker:</b> Slices 70% cash into balance at +0.35R and moves SL to Break-Even.\n"
            f"4. <b>Risk Floor:</b> Fixed 2% risk per asset. Zero martingale."
        )

    def handle_vip(self) -> str:
        return (
            f"💎 <b>VIP Access:</b>\n\n"
            f"Get all live signals and real-time trade management:\n"
            f"1. <b>Free via Partner Broker:</b> Open & fund an account via our link, then message {self.admin_contact}.\n"
            f"2. <b>Direct:</b> 3,000 KES / $25 USD monthly.\n\n"
            f"DM {self.admin_contact} for details."
        )

    def handle_broker(self) -> str:
        return (
            f"🏦 <b>Recommended Broker:</b>\n"
            f"👉 <a href='{self.broker_link}'>{self.broker_link}</a>\n\n"
            f"• Use Cent account for capital under $100.\n"
            f"• Standard / Raw account for $200+.\n"
            f"• Leverage: 1:500 or higher."
        )

    def handle_natural_language(self, text: str) -> Optional[str]:
        """Detects keywords and returns calm, helpful answers."""
        t = text.lower()

        if any(k in t for k in ["how much", "capital", "pesa ngapi", "minimum", "deposit", "kuanza"]):
            return (
                "You can start with $20 - $50 on an MT5 Cent account. "
                "Risk is strictly 2% per trade. Type /broker for setup details."
            )

        if any(k in t for k in ["bot", "automated", "automatic", "robot", "inafanya kazi aje", "auto"]):
            return (
                "Yes, our system runs autonomously on MT5. It scans 29 pairs, executes, and trails stops automatically. "
                "Type /status to see the live account."
            )

        if any(k in t for k in ["join", "vip", "kuingia"]):
            return (
                f"To join VIP, type /vip or message {self.admin_contact} directly."
            )

        if any(k in t for k in ["real", "legit", "proof", "profitable"]):
            return (
                "Type /status to see our live MT5 equity, balance, and open positions in real time."
            )

        return None

    # =========================================================================
    # CORE POLLING LOOP
    # =========================================================================
    def process_update(self, update: Dict[str, Any]):
        """Processes a single incoming Telegram update."""
        msg = update.get("message") or update.get("channel_post")
        if not msg:
            return

        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = (msg.get("text") or "").strip()
        from_user = msg.get("from", {})
        first_name = from_user.get("first_name", "Trader")

        # 1. New chat member greeting (clean and short)
        new_members = msg.get("new_chat_members", [])
        if new_members:
            for nm in new_members:
                name = nm.get("first_name", "Trader")
                welcome_card = (
                    f"Welcome {name} to Sajim Traders.\n"
                    f"Check /status for live account metrics or /strategy to see how our engine operates."
                )
                self.send_message(chat_id, welcome_card)
            return

        if not text:
            return

        cmd = text.split()[0].lower().replace("@sajim_quant_bot", "")

        # 2. Command Dispatch
        if cmd in ("/start", "/help", "help"):
            resp = self.handle_start(chat_id, first_name)
            self.send_message(chat_id, resp)
        elif cmd in ("/status", "/live", "status"):
            resp = self.handle_status()
            self.send_message(chat_id, resp)
        elif cmd in ("/strategy", "/how", "strategy"):
            resp = self.handle_strategy()
            self.send_message(chat_id, resp)
        elif cmd in ("/vip", "/join", "vip"):
            resp = self.handle_vip()
            self.send_message(chat_id, resp)
        elif cmd in ("/broker", "/register", "broker"):
            resp = self.handle_broker()
            self.send_message(chat_id, resp)
        else:
            # 3. Natural Language Assistant
            ai_reply = self.handle_natural_language(text)
            if ai_reply:
                self.send_message(chat_id, ai_reply)

    def _poll_loop(self):
        """Background worker that continuously pulls updates from Telegram."""
        logger.info("[+] Sajim Community Concierge active (calm mode).")
        while self.is_running:
            if not self.bot_token:
                time.sleep(5.0)
                self.load_config()
                continue

            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates?offset={self.last_update_id + 1}&timeout=15"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=20.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                if data.get("ok"):
                    for update in data.get("result", []):
                        uid = update.get("update_id", 0)
                        if uid > self.last_update_id:
                            self.last_update_id = uid
                        self.process_update(update)
            except Exception as e:
                time.sleep(2.0)

    def start(self):
        """Starts the concierge listener in a background daemon thread."""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self.worker_thread.start()
            logger.info("[+] Community Concierge listening.")

    def stop(self):
        """Stops the concierge listener."""
        self.is_running = False


# Singleton runner
_concierge_instance = None

def get_concierge() -> SajimCommunityConcierge:
    global _concierge_instance
    if _concierge_instance is None:
        _concierge_instance = SajimCommunityConcierge()
    return _concierge_instance

if __name__ == "__main__":
    print("=" * 80)
    print("      SAJIM HOLDINGS — COMMUNITY CONCIERGE & CONVERSION AI")
    print("=" * 80)
    concierge = get_concierge()
    concierge.start()
    print("[+] Concierge AI is running. Send /start, /status, /vip in Telegram to interact.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[!] Stopping Concierge AI.")
        concierge.stop()
