import subprocess
import MetaTrader5 as mt5

print("=== CHECKING WMIC PROCESSES ===")
try:
    res = subprocess.run('wmic process where "name=\'terminal64.exe\'" get ProcessId,ExecutablePath,CommandLine', capture_output=True, text=True, shell=True)
    print(res.stdout)
except Exception as e:
    print("WMIC error:", e)

print("\n=== CHECKING DEFAULT MT5 CONNECTION ===")
if mt5.initialize():
    acc = mt5.account_info()
    term = mt5.terminal_info()
    print("Default Init:")
    print("  Terminal Path:", term.path)
    print("  Data Path:    ", term.data_path)
    print("  Server:       ", acc.server if acc else "None")
    print("  Login:        ", acc.login if acc else "None")
    print("  Balance:      ", acc.balance if acc else "None")
    print("  Currency:     ", acc.currency if acc else "None")
    mt5.shutdown()
else:
    print("Default Init Failed:", mt5.last_error())

# Check Headway Terminal explicitly
p_headway = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
print(f"\n=== CHECKING HEADWAY TERMINAL ({p_headway}) ===")
if mt5.initialize(path=p_headway, timeout=5000):
    acc = mt5.account_info()
    term = mt5.terminal_info()
    print("  Terminal Path:", term.path)
    print("  Server:       ", acc.server if acc else "None")
    print("  Login:        ", acc.login if acc else "None")
    print("  Balance:      ", acc.balance if acc else "None")
    mt5.shutdown()
else:
    print("  Headway Init Failed:", mt5.last_error())
