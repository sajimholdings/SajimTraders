import MetaTrader5 as mt5
import sys

HEADWAY_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
LOGIN = 17537803
PASSWORD = "Jimmy123!"
SERVER = "Headway-Real"

print("--- INITIALIZING MT5 TERMINAL ---", flush=True)
print(f"Terminal Path: {HEADWAY_PATH}", flush=True)

if not mt5.initialize(path=HEADWAY_PATH):
    print("mt5.initialize failed, error:", mt5.last_error(), flush=True)
    sys.exit(1)

print("mt5.initialize SUCCESSFUL!", flush=True)

# Attempt login
print(f"Logging in to {LOGIN} on server {SERVER}...")
authorized = mt5.login(login=LOGIN, password=PASSWORD, server=SERVER)

if not authorized:
    print(f"Login failed! Error: {mt5.last_error()}")
    acc = mt5.account_info()
    if acc:
        print(f"Current Account: {acc.login}, Server: {acc.server}")
else:
    print("mt5.login SUCCESSFUL!")

acc = mt5.account_info()
if acc is not None:
    print("\n==========================================")
    print("        HEADWAY ACCOUNT VERIFICATION      ")
    print("==========================================")
    print(f"Login:         {acc.login}")
    print(f"Name:          {acc.name}")
    print(f"Server:        {acc.server}")
    print(f"Currency:      {acc.currency}")
    print(f"Balance:       {acc.balance} {acc.currency}")
    print(f"Equity:        {acc.equity} {acc.currency}")
    print(f"Leverage:      1:{acc.leverage}")
    print(f"Trade Allowed: {acc.trade_allowed}")
    print(f"Expert Trade:  {acc.trade_expert}")
    print("==========================================\n")
else:
    print("Could not retrieve account info!")
    sys.exit(1)

# Inspect symbols
print("--- QUERYING HEADWAY SYMBOLS ---")
symbols = mt5.symbols_get()
if symbols:
    print(f"Total symbols found: {len(symbols)}")
    symbol_names = [s.name for s in symbols]
    
    # Check Gold / Metals
    gold_matches = [s for s in symbol_names if "XAU" in s.upper() or "GOLD" in s.upper()]
    silver_matches = [s for s in symbol_names if "XAG" in s.upper() or "SILV" in s.upper()]
    print(f"Gold symbols: {gold_matches}")
    print(f"Silver symbols: {silver_matches}")
    
    # Check FX
    fx_pairs = ["EURUSD", "GBPUSD", "USDJPY", "GBPJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]
    found_fx = []
    for fx in fx_pairs:
        matches = [s for s in symbol_names if fx in s.upper()]
        found_fx.extend(matches)
    print(f"FX matches: {found_fx}")
    
    # Check Indices / Crypto
    indices = [s for s in symbol_names if any(k in s.upper() for k in ["US100", "NAS", "US30", "SPX", "BTC"])]
    print(f"Indices/Crypto matches: {indices[:10]}")
else:
    print("No symbols retrieved or error:", mt5.last_error())

mt5.shutdown()
print("\n--- TEST COMPLETE ---")
