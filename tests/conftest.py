"""Shared pytest setup.

- Puts the repo root on sys.path.
- Falls back to a safe MetaTrader5 stub (tests/stubs) when the real Windows-only
  package is unavailable, so MT5-dependent modules can be imported on Linux/CI.
- Skips test modules that need the private BEEP engines (core/beep_*, vault/),
  which are intentionally not committed to this repository.
"""
import importlib.util
import os
import re
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TESTS_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

if importlib.util.find_spec("MetaTrader5") is None:
    sys.path.insert(0, os.path.join(TESTS_DIR, "stubs"))

_PRIVATE_IMPORT = re.compile(
    r"^\s*(from|import)\s+(core\.)?(beep_\w+|tick_beep_engine|vault_original_beep)\b", re.M
)
_PRIVATE_AVAILABLE = os.path.exists(os.path.join(ROOT_DIR, "core", "beep_core.py"))

collect_ignore = []
if not _PRIVATE_AVAILABLE:
    for name in sorted(os.listdir(TESTS_DIR)):
        if name.startswith("test_") and name.endswith(".py"):
            with open(os.path.join(TESTS_DIR, name), encoding="utf-8", errors="ignore") as fh:
                if _PRIVATE_IMPORT.search(fh.read()):
                    collect_ignore.append(name)
