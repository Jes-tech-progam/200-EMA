import os
import alpaca_trade_api as tradeapi
import pandas as pd
import ta
from datetime import datetime, timedelta

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = "https://paper-api.alpaca.markets"

api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL)

TIMEFRAME = "1Week"
EMA_PERIOD = 200

# 🔥 Top stocks (you can expand this later)
SYMBOLS = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL",
    "META","TSLA","AVGO","LLY","BRK.B"
]

def get_data(symbol):
    try:
        end = datetime.utcnow()
        start = end - timedelta(weeks=300)

        df = api.get_bars(
            symbol,
            TIMEFRAME,
            start.isoformat(),
            end.isoformat()
        ).df

        return df

    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def add_ema(df):
    df['ema'] = ta.trend.ema_indicator(df['close'], window=EMA_PERIOD)
    return df

def check_signal(df):
    df = df.dropna()

    if len(df) < 210:
        return False

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    # ✅ EMA pullback + bounce strategy
    if (
        prev['close'] > prev['ema'] and      # uptrend
        curr['low'] <= curr['ema'] and       # touches EMA
        curr['close'] > curr['ema'] and      # bounce
        curr['ema'] > df.iloc[-10]['ema']    # EMA trending up
    ):
        return True

    return False

def already_in_position(symbol):
    positions = api.list_positions()
    for pos in positions:
        if pos.symbol == symbol:
            return True
    return False

def place_order(symbol):
    if already_in_position(symbol):
        print(f"Already holding {symbol}")
        return

    print(f"🚀 BUY SIGNAL: {symbol}")
    api.submit_order(
        symbol=symbol,
        qty=1,
        side='buy',
        type='market',
        time_in_force='gtc'
    )

def run_scanner():
    print("Scanning market...\n")

    for symbol in SYMBOLS:
        df = get_data(symbol)
        if df is None or df.empty:
            continue

        df = add_ema(df)

        if check_signal(df):
            print(f"✅ Signal found: {symbol}")
            place_order(symbol)
        else:
            print(f"No setup: {symbol}")

if __name__ == "__main__":
    run_scanner()