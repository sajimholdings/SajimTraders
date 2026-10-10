"""
core/lot_calculator.py
========================================================================================
            SAJIM HOLDINGS — UNIVERSAL LOT CALCULATOR (core/lot_calculator.py)
========================================================================================
Chief Architect: Jimmy Mathu
Scale-Invariant Dynamic Position Sizing for Universal Account Tiers ($1 to $100,000+).
Supports: Cent Accounts (USC), Standard Accounts (USD), Micro/Pro Accounts (1:30 - 1:3000).
========================================================================================
"""

import math
from typing import Tuple, Dict, Any, Optional
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False


CENT_CURRENCIES = {"USC", "EUC", "GBC", "EUX", "GBX", "JPC", "AUC", "CAC", "CHC"}


def _step_decimals(step: float) -> int:
    """Decimals implied by a broker volume step (0.01 -> 2, 0.1 -> 1, 0.5 -> 1, 1 -> 0)."""
    if not step or step <= 0:
        return 2
    return len(f"{float(step):.10f}".rstrip("0").split(".")[1])


def _floor_to_step(value: float, step: float) -> float:
    return round(math.floor((value + 1e-9) / step) * step, _step_decimals(step))


def _account_currency(account_currency: Optional[str]) -> Optional[str]:
    if account_currency:
        return account_currency
    if MT5_AVAILABLE and mt5 is not None:
        try:
            acc = mt5.account_info()
            if acc is not None:
                return getattr(acc, "currency", None)
        except Exception:
            pass
    return None


def _is_cent(account_currency: Optional[str]) -> bool:
    if not account_currency:
        return False
    return account_currency.upper() in CENT_CURRENCIES or "cent" in account_currency.lower()


class UniversalLotCalculator:
    """
    Computes mathematically exact lot sizing for ANY asset class on ANY broker:
    Forex, Metals, Crypto, Indices, Commodities.

    Safety contract (callers MUST honour it):
      - Returns lot = 0.0 when the trade cannot be sized within the risk budget
        (zero stop distance, zero/negative equity, or broker minimum lot would exceed
        the requested risk). specs["rejected"] carries the reason.
      - Lots are FLOORED to the broker volume_step, never rounded up.
    """

    @staticmethod
    def _reject(reason: str, risk_cash: float = 0.0, **extra: Any) -> Tuple[float, float, Dict[str, Any]]:
        specs: Dict[str, Any] = {"rejected": reason, "target_risk_cash": round(risk_cash, 2),
                                 "actual_risk_cash": 0.0, "actual_risk_pct": 0.0}
        specs.update(extra)
        return 0.0, 0.0, specs

    @staticmethod
    def calculate_lot(
        symbol: str,
        equity: float,
        risk_fraction: float,
        entry_price: float,
        stop_price: float,
        account_currency: Optional[str] = None,
    ) -> Tuple[float, float, Dict[str, Any]]:
        """
        Returns: (executable_lot, cash_at_risk, debug_specs)
        Formula:
          Risk Cash = Equity * Risk Fraction            (account currency)
          Point Value = TickVal / TickSize              (account currency per 1.0 price unit per lot)
          Raw Lot = Risk Cash / (Stop Distance * Point Value), floored to volume_step
        """
        equity = float(equity or 0.0)
        risk_cash = equity * float(risk_fraction or 0.0)
        stop_dist = abs(float(entry_price) - float(stop_price))

        if equity <= 0:
            return UniversalLotCalculator._reject("non-positive equity", risk_cash)
        if risk_cash <= 0:
            return UniversalLotCalculator._reject("non-positive risk budget", risk_cash)
        if stop_dist <= 0:
            return UniversalLotCalculator._reject("zero stop distance", risk_cash)

        if not MT5_AVAILABLE or mt5 is None:
            # Offline approximation (1 account unit per price unit per lot) for research only.
            vol_min, vol_step, vol_max = 0.01, 0.01, 0.05
            raw_lot = risk_cash / stop_dist
            clean_lot = min(vol_max, _floor_to_step(raw_lot, vol_step))
            if clean_lot < vol_min:
                return UniversalLotCalculator._reject(
                    "min lot exceeds risk budget", risk_cash, min_lot_risk_cash=round(vol_min * stop_dist, 2))
            actual_risk = clean_lot * stop_dist
            specs = {
                "tick_val": 1.0,
                "tick_size": 0.00001,
                "point_val": 1.0,
                "vol_min": vol_min,
                "vol_step": vol_step,
                "vol_max": vol_max,
                "target_risk_cash": round(risk_cash, 2),
                "actual_risk_cash": round(actual_risk, 2),
                "actual_risk_pct": round((actual_risk / equity) * 100.0, 2),
                "offline_approximation": True,
            }
            return clean_lot, actual_risk, specs

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            raise ValueError(f"Symbol {symbol} info not found on broker.")

        currency = _account_currency(account_currency)
        is_cent = _is_cent(currency) if currency else symbol.endswith(".c")

        tick_val = symbol_info.trade_tick_value
        tick_size = symbol_info.trade_tick_size or symbol_info.point

        if tick_val is None or tick_val <= 0:
            # Fallback for newly subscribed instruments without tick value
            contract_size = symbol_info.trade_contract_size or (1.0 if "XAU" in symbol else 1000.0)
            if is_cent:
                # On Cent accounts (USC), 1 USD = 100 USC
                if "JPY" in symbol:
                    jpy_rate = entry_price if entry_price > 10.0 else 150.0
                    point_value = (contract_size * 100.0) / jpy_rate
                else:
                    point_value = contract_size * 100.0
                tick_val = point_value * (tick_size or symbol_info.point)
            else:
                tick_val = max(1e-6, contract_size * (tick_size or symbol_info.point))
                point_value = tick_val / tick_size if tick_size > 0 else 1.0
        else:
            point_value = tick_val / tick_size if tick_size > 0 else 1.0

        vol_min = symbol_info.volume_min or 0.01
        vol_step = symbol_info.volume_step or 0.01
        vol_max = symbol_info.volume_max or 100.0

        if point_value <= 0:
            return UniversalLotCalculator._reject("invalid point value", risk_cash)

        # Exact raw lot calculation
        raw_lot = risk_cash / (stop_dist * point_value)

        # Strict Small-Account Risk Guardian (thresholds in USD; cent equity normalised to USD)
        equity_major = equity / 100.0 if is_cent else equity
        if equity_major < 50.0:
            equity_lot_ceiling = 0.02 if ("JPY" in symbol or "USD" in symbol) else 0.01
            vol_max = min(vol_max, equity_lot_ceiling)
        elif equity_major < 100.0:
            equity_lot_ceiling = 0.05 if ("JPY" in symbol or "USD" in symbol) else 0.02
            vol_max = min(vol_max, equity_lot_ceiling)
        elif equity_major < 250.0:
            equity_lot_ceiling = 0.10 if ("JPY" in symbol or "USD" in symbol) else 0.05
            vol_max = min(vol_max, equity_lot_ceiling)

        # Floor to broker lot step (never round up) and cap at max
        clean_lot = min(_floor_to_step(raw_lot, vol_step), _floor_to_step(vol_max, vol_step))
        if clean_lot + 1e-12 < vol_min:
            min_lot_risk = vol_min * stop_dist * point_value
            return UniversalLotCalculator._reject(
                "min lot exceeds risk budget", risk_cash,
                min_lot_risk_cash=round(min_lot_risk, 2), vol_min=vol_min, vol_step=vol_step,
            )
        clean_lot = round(clean_lot, _step_decimals(vol_step))

        actual_risk_cash = clean_lot * stop_dist * point_value

        specs = {
            "tick_val": tick_val,
            "tick_size": tick_size,
            "point_val": point_value,
            "vol_min": vol_min,
            "vol_step": vol_step,
            "vol_max": vol_max,
            "account_currency": currency,
            "is_cent_account": is_cent,
            "target_risk_cash": round(risk_cash, 2),
            "actual_risk_cash": round(actual_risk_cash, 2),
            "actual_risk_pct": round((actual_risk_cash / equity) * 100.0, 2),
        }
        return clean_lot, actual_risk_cash, specs
