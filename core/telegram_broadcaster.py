"""
========================================================================================
            SAJIM HOLDINGS — TELEGRAM BROADCAST DISPATCHER
                      (core/telegram_broadcaster.py)
========================================================================================
Chief Architect: Jimmy Mathu
Mission:
  Dispatches real-time institutional BEEP signals, cash milking updates, Break-Even
  ratchet notifications, and PnL proof cards directly to Telegram VIP channels and groups.

Design:
  - Completely non-blocking: Runs in a dedicated background worker queue so Telegram
    network latency NEVER delays live MT5 trade execution.
  - Zero heavy dependencies: Uses standard library urllib.request with robust error handling.
  - Rate-limit aware: Debounced dispatch prevents Telegram API 429 Flood Waits.
  - Configurable: Reads from config/telegram_config.json or environment variables.
========================================================================================
"""

import os
import sys
import json
import time
import queue
import threading
import logging
import urllib.request
import urllib.parse
import re
import html
from typing import Optional, Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
CONFIG_FILE = os.path.join(ROOT_DIR, "config", "telegram_config.json")

logger = logging.getLogger("TelegramBroadcaster")


class TelegramBroadcaster:
    """
    Thread-safe, non-blocking Telegram Channel Dispatcher.
    Queues outgoing messages and flushes them asynchronously.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TelegramBroadcaster, cls).__new__(cls)
                cls._instance._init_broadcaster()
            return cls._instance

    def _init_broadcaster(self):
        self.bot_token: Optional[str] = None
        self.free_channel_id: Optional[str] = None
        self.vip_channel_id: Optional[str] = None
        self.channel_id: Optional[str] = None
        self.enabled: bool = False
        self.message_queue: queue.Queue = queue.Queue(maxsize=1000)
        self.worker_thread: Optional[threading.Thread] = None
        self.is_running: bool = False

        self.load_config()
        self.start_worker()

    def load_config(self):
        """Loads bot_token, free_channel_id, and vip_channel_id from config file or environment."""
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.free_channel_id = os.getenv("TELEGRAM_FREE_CHAT_ID")
        self.vip_channel_id = os.getenv("TELEGRAM_VIP_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHANNEL_ID")

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.bot_token = self.bot_token or data.get("bot_token")
                    self.free_channel_id = self.free_channel_id or data.get("free_channel_id") or data.get("channel_id")
                    self.vip_channel_id = self.vip_channel_id or data.get("vip_channel_id")
            except Exception as e:
                logger.warning(f"Failed to read telegram config: {e}")

        # Primary fallback
        self.channel_id = self.vip_channel_id or self.free_channel_id

        # Check if active credentials are present
        if (
            self.bot_token
            and (self.free_channel_id or self.vip_channel_id)
            and "YOUR_BOT_TOKEN" not in self.bot_token
        ):
            self.enabled = True
            logger.info(f"[+] Telegram Broadcaster ARMED: Free=[{self.free_channel_id}] | VIP=[{self.vip_channel_id or 'STANDBY'}]")
        else:
            self.enabled = False
            logger.info("[-] Telegram Broadcaster STANDBY (Credentials missing or placeholder).")

    def start_worker(self):
        """Launches the background consumer thread."""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()

    def _worker_loop(self):
        """Continuously pulls messages from queue and delivers via HTTP API."""
        while self.is_running:
            try:
                item = self.message_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            target_chat_id, text, parse_mode = item
            if self.enabled and self.bot_token and target_chat_id:
                self._dispatch_http(target_chat_id, text, parse_mode)
                # Rate-limit safety: 1 second pause between broadcast messages
                time.sleep(1.0)
            self.message_queue.task_done()

    @staticmethod
    def sanitize_telegram_html(text: str) -> str:
        """
        Sanitizes arbitrary text containing HTML markup for Telegram's strict HTML parser.
        Escapes rogue '&', '<', and '>' while preserving valid Telegram HTML tags.
        """
        if not text:
            return ""
        # 1. Escape ampersands not part of an existing valid entity
        text = re.sub(r'&(?!(?:amp|lt|gt|quot|#\d+);)', '&amp;', text)
        # 3. Escape any '<' that is NOT an allowed Telegram HTML tag
        allowed_tags = r'/?(?:b|strong|i|em|u|s|strike|del|span|tg-spoiler|a|code|pre|blockquote)\b'
        text = re.sub(rf'<(?!(?:{allowed_tags}))', '&lt;', text, flags=re.IGNORECASE)
        # 4. Escape any standalone '>' that does not cleanly close a tag
        text = re.sub(r'(?<=\s)>|(?<=\d)>', '&gt;', text)
        return text

    def _dispatch_http(self, target_chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
        """Raw HTTP POST request to Telegram Bot API with pre-flight sanitization."""
        if parse_mode == "HTML":
            text = self.sanitize_telegram_html(text)

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")

        for attempt in range(1, 4):
            try:
                with urllib.request.urlopen(req, timeout=8.0) as resp:
                    if resp.status == 200:
                        logger.info(f"[📢 TELEGRAM SENT] Delivered successfully to {target_chat_id}")
                        return True
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                logger.error(f"[-] Telegram HTTPError {e.code} on attempt {attempt}: {err_body}")
                if e.code == 400 and payload.get("parse_mode"):
                    # Fallback to clean plain text (strip all HTML tags completely)
                    logger.info("[!] Retrying Telegram dispatch as clean plain text fallback...")
                    clean_text = re.sub(r'<[^>]+>', '', text)
                    payload.pop("parse_mode", None)
                    payload["text"] = clean_text
                    data = urllib.parse.urlencode(payload).encode("utf-8")
                    req = urllib.request.Request(url, data=data, method="POST")
                    continue
                if e.code == 429:
                    time.sleep(5.0)  # Rate limit backoff
            except Exception as e:
                logger.warning(f"[-] Telegram network error on attempt {attempt}: {e}")
                time.sleep(2.0)

        return False

    def send_broadcast(self, text: str, parse_mode: str = "HTML", target: str = "vip"):
        """
        Public API: Enqueues a message for non-blocking asynchronous transmission.
        target options:
          - 'vip'   : Dispatches exclusively to VIP channel.
          - 'free'  : Dispatches exclusively to Free public channel.
          - 'proof' : Dispatches to both VIP and Free channel (milked cash, TP smashed).
          - 'all'   : Dispatches to both channels.
        """
        if not self.enabled:
            self.load_config()
        if not self.enabled:
            return

        # 1. VIP Channel
        if target in ("vip", "all", "proof"):
            if self.vip_channel_id:
                try:
                    self.message_queue.put_nowait((self.vip_channel_id, text, parse_mode))
                except queue.Full:
                    logger.warning("[-] Telegram VIP queue full, dropping alert.")

        # 2. Free Public Channel
        if target in ("free", "all", "proof"):
            if self.free_channel_id:
                try:
                    self.message_queue.put_nowait((self.free_channel_id, text, parse_mode))
                except queue.Full:
                    logger.warning("[-] Telegram Free queue full, dropping alert.")


# Singleton helper function
def send_telegram_card(text: str, parse_mode: str = "HTML", target: str = "vip"):
    broadcaster = TelegramBroadcaster()
    broadcaster.send_broadcast(text, parse_mode=parse_mode, target=target)
