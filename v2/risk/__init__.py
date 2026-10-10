"""
SAJIM V2 RISK PACKAGE (lazy exports; sub-modules import independently)
"""
import importlib

_LAZY_EXPORTS = {
    "HummingbirdEvaluator": ("v2.risk.hummingbird", "HummingbirdEvaluator"),
    "V2PositionRiskManager": ("v2.risk.ratchet", "V2PositionRiskManager"),
    "PositionStateStore": ("v2.risk.position_state", "PositionStateStore"),
}

__all__ = list(_LAZY_EXPORTS)


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        module_name, attr = _LAZY_EXPORTS[name]
        return getattr(importlib.import_module(module_name), attr)
    raise AttributeError(f"module 'v2.risk' has no attribute {name!r}")
