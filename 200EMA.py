import os
import alpaca_trade_api as tradeapi
import pandas as pd
import ta
from datetime import datetime, timedelta

# ✅ CORRECT ENV VARIABLES (Alpaca standard)
API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = "https://paper-api.alpaca.markets"

# Safety check
if not API_KEY or not SECRET_KEY:
    raise ValueError("Missing Alpaca API keys. Check Railway environment variables.")

api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL)

# ⚙️ SETTINGS
TIMEFRAME = "1Week"
EMA_PERIOD = 200
MAX_TRADES = 3  # limit number of buys per run

# 📊 STOCK LIST (expand later if needed)
SYMBOLS = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL",
    "META","TSLA","AVGO","LLY","BRK.B"
]

# 📥 Fetch data
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
        print(f"❌ Error fetching {symbol}: {e}")
        return None

# 📈 Add EMA
def add_ema(df):
    df['ema'] = ta.trend.ema_indicator(df['close'], window=EMA_PERIOD)
    return df

# 🔍 Strategy logic
def check_signal(df):
    df = df.dropna()

    if len(df) < 210:
        return False, 0

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    # ✅ EMA pullback + bounce
    if (
        prev['close'] > prev['ema'] and
        curr['low'] <= curr['ema'] and
        curr['close'] > curr['ema'] and
        curr['ema'] > df.iloc[-10]['ema']  # EMA trending up
    ):
        # score = strength of bounce
        score = (curr['close'] - curr['ema']) / curr['ema']
        return True, score

    return False, 0

# 💼 Check if already holding
def already_in_position(symbol):
    try:
        positions = api.list_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return True
    except:
        pass
    return False

# 💰 Execute trade
def place_order(symbol):
    if already_in_position(symbol):
        print(f"⚠️ Already holding {symbol}")
        return False

    try:
        print(f"🚀 BUY: {symbol}")
        api.submit_order(
            symbol=symbol,
            qty=1,
            side='buy',
            type='market',
            time_in_force='gtc'
        )
        return True
    except Exception as e:
        print(f"❌ Order failed for {symbol}: {e}")
        return False

# 🔎 Main scanner
def run_scanner():
    print("🔍 Scanning market...\n")

    signals = []

    for symbol in SYMBOLS:
        df = get_data(symbol)
        if df is None or df.empty:
            continue

        df = add_ema(df)

        signal, score = check_signal(df)

        if signal:
            print(f"✅ Signal: {symbol} | Score: {round(score,4)}")
            signals.append((symbol, score))
        else:
            print(f"No setup: {symbol}")

    # 🔥 Sort best setups
    signals.sort(key=lambda x: x[1], reverse=True)

    print("\n🏆 Top setups:")
    for s in signals:
        print(s)

    # 🚀 Execute top trades
    trades = 0
    for symbol, score in signals:
        if trades >= MAX_TRADES:
            break

        if place_order(symbol):
            trades += 1

    print(f"\n✅ Trades executed: {trades}")

# ▶️ Run bot
if __name__ == "__main__":
    run_scanner()
