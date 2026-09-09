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
import MetaTrader5 as mt5


class UniversalLotCalculator:
    """
    Computes mathematically exact lot sizing for ANY asset class on ANY broker:
    Forex, Metals, Crypto, Indices, Commodities.
    """

    @staticmethod
    def calculate_lot(
        symbol: str,
        equity: float,
        risk_fraction: float,
        entry_price: float,
        stop_price: float,
    ) -> Tuple[float, float, Dict[str, Any]]:
        """
        Returns: (executable_lot, cash_at_risk, debug_specs)
        Formula:
          Risk Cash ($) = Equity * Risk Fraction
          Point Value ($ per point move per 1.0 Lot) = TickVal / TickSize
          Raw Lot = Risk Cash / (Stop Distance * Point Value)
        """
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            raise ValueError(f"Symbol {symbol} info not found on broker.")

        stop_dist = abs(entry_price - stop_price)
        if stop_dist <= 0:
            stop_dist = symbol_info.point * 50.0

        tick_val = symbol_info.trade_tick_value
        tick_size = symbol_info.trade_tick_size or symbol_info.point
        is_cent = symbol.endswith(".c")

        if tick_val is None or tick_val <= 0:
            # Fallback for cent accounts and newly subscribed instruments
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
            point_value = 1.0
        risk_cash = equity * risk_fraction

        # Exact raw lot calculation
        raw_lot = risk_cash / max(1e-6, (stop_dist * point_value))

        # Snap to broker lot step and clamp
        steps = round((raw_lot - vol_min) / vol_step)
        clean_lot = vol_min + (steps * vol_step)
        clean_lot = max(vol_min, min(vol_max, clean_lot))
        clean_lot = round(clean_lot, 2)

        actual_risk_cash = clean_lot * stop_dist * point_value

        specs = {
            "tick_val": tick_val,
            "tick_size": tick_size,
            "point_val": point_value,
            "vol_min": vol_min,
            "vol_step": vol_step,
            "vol_max": vol_max,
            "target_risk_cash": round(risk_cash, 2),
            "actual_risk_cash": round(actual_risk_cash, 2),
            "actual_risk_pct": round((actual_risk_cash / equity) * 100.0, 2),
        }
        return clean_lot, actual_risk_cash, specs
