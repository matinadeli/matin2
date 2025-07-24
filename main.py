import os
import time
import requests
import pandas as pd
from flask import Flask, request
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import ADXIndicator

# تنظیمات ربات تلگرام
BOT_TOKEN = "7950619090:AAGafe0s5xwEDxXIytd-OFybum3tUCuOZPI"
CHAT_ID = "423311697"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

# لیست ارزهای منتخب
COINS = ["bitcoin", "ethereum", "bnb", "solana", "ripple"]

# توابع ارسال پیام
def telegram_send_message(text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=data)

# تابع دریافت قیمت‌ها از CoinCap
def fetch_ohlcv(coin):
    url = f"https://api.coincap.io/v2/assets/{coin}/history?interval=h1"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()["data"]
        df = pd.DataFrame(data)
        df["price"] = df["priceUsd"].astype(float)
        df["time"] = pd.to_datetime(df["time"], unit='ms')
        return df
    return None

# تحلیل تکنیکال و بررسی سیگنال‌ها
def analyze(df):
    df["ema_fast"] = EMAIndicator(df["price"], window=10).ema_indicator()
    df["ema_slow"] = EMAIndicator(df["price"], window=21).ema_indicator()
    df["rsi"] = RSIIndicator(df["price"], window=14).rsi()
    macd = MACD(df["price"])
    df["macd"] = macd.macd_diff()
    stoch = StochasticOscillator(df["price"], df["price"], df["price"], window=14)
    df["stoch"] = stoch.stoch()
    adx = ADXIndicator(df["price"], df["price"], df["price"], window=14)
    df["adx"] = adx.adx()

    latest = df.iloc[-1]

    signals = {
        "ema_cross": latest["ema_fast"] > latest["ema_slow"],
        "rsi": latest["rsi"] > 50,
        "macd": latest["macd"] > 0,
        "stoch": latest["stoch"] > 50,
        "adx": latest["adx"] > 20
    }

    long_signals = sum(signals.values())
    short_signals = 5 - long_signals

    if long_signals >= 3:
        return "LONG 📈"
    elif short_signals >= 3:
        return "SHORT 📉"
    else:
        return "NEUTRAL ⚖️"

# هندلر Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/start":
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": "✅ ربات تحلیل ارز دیجیتال فعال شد!"
            })
        elif text == "/signal":
            reply = "📊 سیگنال‌های بازار:\n\n"
            for coin in COINS:
                df = fetch_ohlcv(coin)
                if df is not None:
                    signal = analyze(df)
                    reply += f"🔹 {coin.capitalize()}: {signal}\n"
                time.sleep(1)
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": reply
            })

    return "OK"

# اجرای اپ Flask
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
