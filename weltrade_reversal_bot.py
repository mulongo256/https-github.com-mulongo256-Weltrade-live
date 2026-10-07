import os
import asyncio
import requests
import pandas as pd
import numpy as np
from metaapi_cloud_sdk import MetaApi

# Weltrade PAINX/GAINX signal-only bot
# No automatic trading. It only reads market data and sends Telegram alerts.

SYMBOLS = {
    "MAX GainX 2000", "MAX PainX 2000", "PainX 1200", "PainX 600",
    "PainX 800", "PainX 999", "GainX 600", "GainX 800", "GainX 999",
    "GainX 1200", "GainX 400", "MAX GainX 1000", "MAX PainX 1000",
    "PainX 400"
}

TIMEFRAMES = ["M1", "M2", "M3", "M4", "M5", "M15", "M20", "M30", "M45", "H1"]

METAAPI_TOKEN = os.getenv("METAAPI_TOKEN")
METAAPI_ACCOUNT_ID = os.getenv("METAAPI_ACCOUNT_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def rsi(values, period=10):
    delta = values.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    ag = gain.ewm(alpha=1 / period, adjust=False).mean()
    al = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = ag / al.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    out = out.where(~((al == 0) & (ag > 0)), 100)
    out = out.where(~((ag == 0) & (al > 0)), 0)
    return out.fillna(50)


def lwma(values, period=7):
    weights = np.arange(1, period + 1)
    return values.rolling(period).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


def make_tf(m1, minutes):
    if minutes == 1:
        return m1
    return m1.resample(f"{minutes}min", label="left", closed="left").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum"
    }).dropna()


def analyse(df):
    if len(df) < 20:
        return None

    typical = (df["high"] + df["low"] + df["close"]) / 3
    df = df.copy()
    df["rsi"] = rsi(typical, 10)

    # Alligator GREEN LINE 1: Teeth 7, shift 0, LWMA, Weighted Close.
    weighted_close = (df["high"] + df["low"] + 2 * df["close"]) / 4
    df["green1"] = lwma(weighted_close, 7)

    # Ichimoku GREEN LINE 2: Tenkan with 1/1/1 settings.
    df["green2"] = (df["high"].rolling(1).max() +
                    df["low"].rolling(1).min()) / 2

    x = df.iloc[-1]
    if not np.isfinite(x["rsi"]) or not np.isfinite(x["green1"]) or not np.isfinite(x["green2"]):
        return None

    # Price-domain green lines are mapped to their position inside the
    # current candle range so they can be evaluated against RSI 0..100.
    rng = float(x["high"] - x["low"])
    if rng <= 0:
        return None

    g1 = float(np.clip(100 * (x["green1"] - x["low"]) / rng, 0, 100))
    g2 = float(np.clip(100 * (x["green2"] - x["low"]) / rng, 0, 100))
    rv = float(x["rsi"])

    buy = 0 <= rv <= 10 and 0 <= g1 <= 10 and 0 <= g2 <= 10
    sell = 90 <= rv <= 100 and 90 <= g1 <= 100 and 90 <= g2 <= 100

    return buy, sell, rv, g1, g2


def telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=20)


async def run():
    if not METAAPI_TOKEN or not METAAPI_ACCOUNT_ID:
        raise RuntimeError("Set METAAPI_TOKEN and METAAPI_ACCOUNT_ID.")

    api = MetaApi(METAAPI_TOKEN)
    account = await api.metatrader_account_api.get_account(METAAPI_ACCOUNT_ID)
    await account.wait_connected()

    connection = account.get_rpc_connection()
    await connection.connect()
    await connection.wait_synchronized()

    print("Connected to Weltrade through MetaApi.")

    while True:
        for symbol in sorted(SYMBOLS):
            try:
                candles = await connection.get_candles(symbol, "1m", None, 5000)
                rows = []
                for c in candles:
                    rows.append({
                        "time": pd.to_datetime(c["time"], utc=True),
                        "open": float(c["open"]),
                        "high": float(c["high"]),
                        "low": float(c["low"]),
                        "close": float(c["close"]),
                        "volume": float(c.get("volume", 0))
                    })

                m1 = pd.DataFrame(rows).set_index("time").sort_index()

                votes_buy = 0
                votes_sell = 0

                for tf in TIMEFRAMES:
                    minutes = 60 if tf == "H1" else int(tf[1:])
                    result = analyse(make_tf(m1, minutes))
                    if result:
                        buy, sell, *_ = result
                        votes_buy += int(buy)
                        votes_sell += int(sell)

                if votes_buy == 10:
                    telegram(
                        f"BUY CONFIRMED\n"
                        f"Symbol: {symbol}\n"
                        f"Agreement: 10/10\n"
                        f"TP1: RSI 50\n"
                        f"Invalidation: RSI 0\n"
                        f"Signal only - no automatic trade."
                    )

                elif votes_sell == 10:
                    telegram(
                        f"SELL CONFIRMED\n"
                        f"Symbol: {symbol}\n"
                        f"Agreement: 10/10\n"
                        f"TP1: RSI 50\n"
                        f"Invalidation: RSI 100\n"
                        f"Signal only - no automatic trade."
                    )

            except Exception as e:
                print(f"{symbol}: {e}")

        await asyncio.sleep(int(os.getenv("POLL_SECONDS", "15")))


if __name__ == "__main__":
    asyncio.run(run())
