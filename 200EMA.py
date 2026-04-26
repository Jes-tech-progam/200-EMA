import os
import alpaca_trade_api as tradeapi
import pandas as pd
import ta
from datetime import datetime, timedelta, timezone

# =========================
# 🔐 ALPACA AUTH (Railway safe)
# =========================
API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = "https://paper-api.alpaca.markets"

if not API_KEY or not SECRET_KEY:
    raise ValueError("Missing Alpaca API keys (APCA_API_KEY_ID / APCA_API_SECRET_KEY)")

api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL)

# =========================
# ⚙️ SETTINGS
# =========================
TIMEFRAME = "1Week"
EMA_PERIOD = 200
MAX_TRADES = 3

SYMBOLS = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL",
    "META","TSLA","AVGO","LLY","BRK.B"
]

# =========================
# 📥 GET DATA (FIXED RFC3339)
# =========================
def get_data(symbol):
    try:
        end = datetime.now(timezone.utc)
        start = end - timedelta(weeks=300)

        # FIX: Alpaca-safe format (no microseconds)
        end = end.strftime("%Y-%m-%dT%H:%M:%SZ")
        start = start.strftime("%Y-%m-%dT%H:%M:%SZ")

        df = api.get_bars(
            symbol,
            TIMEFRAME,
            start,
            end
        ).df

        return df

    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
        return None

# =========================
# 📈 EMA CALC
# =========================
def add_ema(df):
    df["ema"] = ta.trend.ema_indicator(df["close"], window=EMA_PERIOD)
    return df

# =========================
# 🔍 STRATEGY LOGIC
# =========================
def check_signal(df):
    df = df.dropna()

    if len(df) < 210:
        return False, 0

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    # EMA pullback + bounce strategy
    if (
        prev["close"] > prev["ema"] and      # uptrend
        curr["low"] <= curr["ema"] and       # touch EMA
        curr["close"] > curr["ema"] and      # bounce
        curr["ema"] > df.iloc[-10]["ema"]    # EMA rising
    ):
        score = (curr["close"] - curr["ema"]) / curr["ema"]
        return True, score

    return False, 0

# =========================
# 💼 POSITION CHECK
# =========================
def already_in_position(symbol):
    try:
        positions = api.list_positions()
        return any(pos.symbol == symbol for pos in positions)
    except:
        return False

# =========================
# 🚀 PLACE ORDER
# =========================
def place_order(symbol):
    if already_in_position(symbol):
        print(f"⚠️ Already holding {symbol}")
        return False

    try:
        print(f"🚀 BUY SIGNAL: {symbol}")
        api.submit_order(
            symbol=symbol,
            qty=1,
            side="buy",
            type="market",
            time_in_force="gtc"
        )
        return True

    except Exception as e:
        print(f"❌ Order failed {symbol}: {e}")
        return False

# =========================
# 🔎 SCANNER
# =========================
def run_scanner():
    print("\n🔍 Scanning market...\n")

    signals = []

    for symbol in SYMBOLS:
        df = get_data(symbol)
        if df is None or df.empty:
            continue

        df = add_ema(df)
        signal, score = check_signal(df)

        if signal:
            print(f"✅ SIGNAL: {symbol} | Score: {round(score,4)}")
            signals.append((symbol, score))
        else:
            print(f"No setup: {symbol}")

    # Sort best setups first
    signals.sort(key=lambda x: x[1], reverse=True)

    print("\n🏆 Top setups:")
    for s in signals:
        print(s)

    # Execute trades (top ones only)
    trades = 0
    for symbol, score in signals:
        if trades >= MAX_TRADES:
            break

        if place_order(symbol):
            trades += 1

    print(f"\n✅ Trades executed: {trades}")

# =========================
# ▶️ RUN
# =========================
if __name__ == "__main__":
    run_scanner()
