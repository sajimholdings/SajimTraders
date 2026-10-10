"""Minimal MetaTrader5 stub so tests can import MT5-dependent modules on Linux/CI.

Only used when the real (Windows-only) MetaTrader5 package is not installed.
Every terminal call fails safely (returns None/False), so nothing can trade.
"""
TIMEFRAME_M1=1; TIMEFRAME_M5=5; TIMEFRAME_M15=15; TIMEFRAME_M30=30; TIMEFRAME_H1=16385; TIMEFRAME_H4=16388; TIMEFRAME_D1=16408
ORDER_TYPE_BUY=0; ORDER_TYPE_SELL=1; POSITION_TYPE_BUY=0; POSITION_TYPE_SELL=1
TRADE_ACTION_DEAL=1; TRADE_ACTION_SLTP=6
ORDER_FILLING_FOK=0; ORDER_FILLING_IOC=1; ORDER_FILLING_RETURN=2; ORDER_TIME_GTC=0
TRADE_RETCODE_DONE=10009; TRADE_RETCODE_REQUOTE=10004; TRADE_RETCODE_PRICE_CHANGED=10020; TRADE_RETCODE_PRICE_OFF=10021; TRADE_RETCODE_INVALID_FILL=10030
DEAL_ENTRY_IN=0; DEAL_ENTRY_OUT=1; DEAL_ENTRY_INOUT=2; DEAL_ENTRY_OUT_BY=3
DEAL_TYPE_BUY=0; DEAL_TYPE_SELL=1
COPY_TICKS_ALL=-1
def initialize(*a, **k): return False
def shutdown(): return None
def login(*a, **k): return False
def last_error(): return (-1, "stub")
def account_info(): return None
def terminal_info(): return None
def symbol_info(s): return None
def symbol_info_tick(s): return None
def symbol_select(s, e=True): return False
def positions_get(*a, **k): return None
def history_deals_get(*a, **k): return None
def history_orders_get(*a, **k): return None
def order_send(r): return None
def order_check(r): return None
def order_calc_margin(*a): return None
def order_calc_profit(*a): return None
def copy_rates_from_pos(*a): return None
def copy_rates_range(*a): return None
def copy_ticks_from(*a): return None
def symbols_get(*a, **k): return None
