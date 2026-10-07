import os
import MetaTrader5 as mt5

login_text = os.getenv("WELTRADE_LOGIN", "").strip()
password = os.getenv("WELTRADE_PASSWORD", "")
server = os.getenv("WELTRADE_SERVER", "").strip() or "Weltrade-Real"

if not login_text or not password:
    print("Missing WELTRADE_LOGIN or WELTRADE_PASSWORD GitHub Secrets.")
    print("The network/DNS tests above are still useful, but MT5 login was not attempted.")
    raise SystemExit(0)

try:
    login = int(login_text)
except ValueError:
    print("WELTRADE_LOGIN must contain only the MT5 account number.")
    raise SystemExit(1)

print(f"Attempting MT5 connection to server: {server}")
print("Password is not printed.")

if not mt5.initialize():
    print("MT5 initialize failed:", mt5.last_error())
    raise SystemExit(1)

try:
    if not mt5.login(login, password=password, server=server):
        print("MT5 login failed:", mt5.last_error())
        raise SystemExit(1)

    info = mt5.account_info()
    if info is None:
        print("Connected, but account_info() returned no data:", mt5.last_error())
        raise SystemExit(1)

    print("SUCCESS: MT5 account connection established.")
    print("Server:", info.server)
    print("Login:", info.login)

    # Read-only market-data test. No trading functions are called.
    symbols = mt5.symbols_get()
    if symbols is None:
        print("Could not list symbols:", mt5.last_error())
        raise SystemExit(1)

    wanted = [
        "MAX GainX 2000", "MAX PainX 2000", "PainX 1200", "PainX 600",
        "PainX 800", "PainX 999", "GainX 600", "GainX 800",
        "GainX 999", "GainX 1200", "GainX 400", "MAX GainX 1000",
        "MAX PainX 1000", "PainX 400"
    ]

    names = {s.name for s in symbols}
    print("Requested symbols found:")
    found = 0
    for name in wanted:
        if name in names:
            print("  YES:", name)
            found += 1
        else:
            print("  NO :", name)

    print(f"Found {found}/{len(wanted)} requested symbols.")

    if "GainX 800" in names:
        if not mt5.symbol_select("GainX 800", True):
            print("GainX 800 exists but could not be selected:", mt5.last_error())
            raise SystemExit(1)

        tick = mt5.symbol_info_tick("GainX 800")
        if tick is None:
            print("GainX 800 selected, but no tick was returned:", mt5.last_error())
            raise SystemExit(1)

        print("LIVE DATA TEST: GainX 800 tick received.")
        print("Bid:", tick.bid)
        print("Ask:", tick.ask)
        print("Time:", tick.time)
    else:
        print("GainX 800 was not found in this MT5 terminal.")

finally:
    mt5.shutdown()
