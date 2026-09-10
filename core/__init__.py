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

try:
    from .sajim_regime_algos import SajimExecutionSuite, AccountProfile
except Exception:
    SajimExecutionSuite, AccountProfile = None, None

try:
    from .beep_binary_quant_engine import run_binary_quant_simulation
except Exception:
    run_binary_quant_simulation = None

try:
    from .tick_beep_engine import TickBeepEngine
except Exception:
    TickBeepEngine = None

try:
    from .backtester import BeepBacktester
except Exception:
    BeepBacktester = None

try:
    from .beep_matrix_scanner import BeepMatrixScanner
except Exception:
    BeepMatrixScanner = None

try:
    from .mt5_bridge import MetaTraderBridge
except Exception:
    MetaTraderBridge = None

try:
    from .beep_broadcast import BeepBroadcastBus
except Exception:
    BeepBroadcastBus = None

try:
    from .lot_calculator import UniversalLotCalculator
except Exception:
    UniversalLotCalculator = None

try:
    from .app import SajimBeepClient, display_sammy_card
except Exception:
    SajimBeepClient, display_sammy_card = None, None

try:
    from .api import BeepApiHandler
except Exception:
    BeepApiHandler = None

try:
    from .beep_processor import BeepProcessor, BeepSnipeFilter, BeepSnipeEvaluation
except Exception:
    BeepProcessor, BeepSnipeFilter, BeepSnipeEvaluation = None, None, None

try:
    from .multi_account_manager import MultiAccountManager, get_multi_account_manager
except Exception:
    MultiAccountManager, get_multi_account_manager = None, None

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
    "MultiAccountManager",
    "get_multi_account_manager",
]
