"""
========================================================================================
           SAJIM HOLDINGS V2 — STRATEGY CARTRIDGES PACKAGE
========================================================================================
Lazy exports: the cartridges depend on the private BEEP processor (core/beep_processor)
at instantiation time; importing this package does not.
"""
import importlib

_LAZY_EXPORTS = {
    "YoungSurgeContinuation": ("v2.strategies.young_surge_continuation", "YoungSurgeContinuation"),
    "ExhaustionMeanReversion": ("v2.strategies.exhaustion_mean_reversion", "ExhaustionMeanReversion"),
    "MirageLiquiditySweepCartridge": ("v2.strategies.mirage_liquidity_sweep", "MirageLiquiditySweepCartridge"),
}

__all__ = list(_LAZY_EXPORTS)


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        module_name, attr = _LAZY_EXPORTS[name]
        return getattr(importlib.import_module(module_name), attr)
    raise AttributeError(f"module 'v2.strategies' has no attribute {name!r}")
