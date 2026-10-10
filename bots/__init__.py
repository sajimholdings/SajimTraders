"""
Sajim Holdings — Production Live Trading Bots
Home to the Sajim V1 Execution, Risk & Capital Management Engine.

Exports are resolved lazily so that importing a sub-module (e.g. bots.prop_firm) does
not require MetaTrader5 or the private BEEP modules (core/beep_*).
"""

import os
import sys
import importlib

BOTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BOTS_DIR, ".."))

for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), BOTS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

_LAZY_EXPORTS = {
    "SajimV1Bot": ("bots.sajim_v1_bot", "SajimV1Bot"),
    "TOXIC_BLACKLIST": ("bots.sajim_v1_bot", "TOXIC_BLACKLIST"),
    "SajimOvernightServer": ("bots.sajim_server_overnight", "SajimOvernightServer"),
    "UniversalLotCalculator": ("core.lot_calculator", "UniversalLotCalculator"),
}

__all__ = list(_LAZY_EXPORTS)


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        module_name, attr = _LAZY_EXPORTS[name]
        return getattr(importlib.import_module(module_name), attr)
    raise AttributeError(f"module 'bots' has no attribute {name!r}")
