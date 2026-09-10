"""
Sajim Holdings — Core Quantitative Engines Package
Provides foundational BEEP mathematical protocols, regime classification,
market scanners, backtesting harnesses, and MT5 terminal bridges.
"""

import os
import sys

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CORE_DIR, ".."))
VAULT_DIR = os.path.join(ROOT_DIR, "vault")

for p in (ROOT_DIR, CORE_DIR, VAULT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

# Resilient imports for proprietary engines (Protected by BEEP Licensing)
try:
    from .beep_core import BeepCoreEngine
except ImportError:
    BeepCoreEngine = None

try:
    from .beep_narrative import BeepNarrativeEngine
except ImportError:
    BeepNarrativeEngine = None

from .sajim_regime_algos import SajimExecutionSuite, AccountProfile

try:
    from .beep_binary_quant_engine import run_binary_quant_simulation
except ImportError:
    run_binary_quant_simulation = None

try:
    from .tick_beep_engine import TickBeepEngine
except ImportError:
    TickBeepEngine = None

from .backtester import BeepBacktester
from .beep_matrix_scanner import BeepMatrixScanner
from .mt5_bridge import MetaTraderBridge
from .beep_broadcast import BeepBroadcastBus
from .lot_calculator import UniversalLotCalculator
from .app import SajimBeepClient, display_sammy_card
from .api import BeepApiHandler

try:
    from .beep_processor import BeepProcessor, BeepSnipeFilter, BeepSnipeEvaluation
except ImportError:
    BeepProcessor, BeepSnipeFilter, BeepSnipeEvaluation = None, None, None

__all__ = [
    "BeepCoreEngine",
    "BeepNarrativeEngine",
    "SajimExecutionSuite",
    "AccountProfile",
    "run_binary_quant_simulation",
    "TickBeepEngine",
    "BeepBacktester",
    "BeepMatrixScanner",
    "MetaTraderBridge",
    "SajimBeepClient",
    "display_sammy_card",
    "BeepApiHandler",
    "BeepProcessor",
    "BeepSnipeFilter",
    "BeepSnipeEvaluation",
]
