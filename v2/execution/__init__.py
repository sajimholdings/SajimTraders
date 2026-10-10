"""
SAJIM V2 EXECUTION PACKAGE (lazy exports; sub-modules import independently)
"""
import importlib

_LAZY_EXPORTS = {
    "V2OrderRouter": ("v2.execution.order_router", "V2OrderRouter"),
}

__all__ = list(_LAZY_EXPORTS)


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        module_name, attr = _LAZY_EXPORTS[name]
        return getattr(importlib.import_module(module_name), attr)
    raise AttributeError(f"module 'v2.execution' has no attribute {name!r}")
