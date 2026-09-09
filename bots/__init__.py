"""
Sajim Holdings — Production Live Trading Bots
Home to the Sajim V1 Execution, Risk & Capital Management Engine.
"""

import os
import sys

BOTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BOTS_DIR, ".."))

for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), BOTS_DIR, os.path.join(ROOT_DIR, "vault")):
    if p not in sys.path:
        sys.path.insert(0, p)

from .sajim_v1_bot import SajimV1Bot, TOXIC_BLACKLIST
from .sajim_server_overnight import SajimOvernightServer
from core.lot_calculator import UniversalLotCalculator

__all__ = [
    "SajimV1Bot",
    "SajimOvernightServer",
    "UniversalLotCalculator",
    "TOXIC_BLACKLIST",
]
