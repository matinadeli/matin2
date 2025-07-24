import threading
import time
import requests
import pandas as pd
from telegram.ext import Updater, CommandHandler
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from flask import Flask
import os

# ----------------- تنظیمات -----------------
ALPHA_VANTAGE_API_KEY = "V4HTD10EH66CQHG6"
BOT_TOKEN = "7950619090:AAGafe0s5xwEDxXIytd-OFybum3tUCuOZPI"
CHAT_ID = "423311697"
CHANNEL_ID = "-1002876171269"

# لیست ارزها (نمادهای Alpha Vantage)
symbols = [
    "BTCUSD", "ETHUSD", "BNBUSD", "SOLUSD", "XRPUSD",
    "ADAUSD", "DOGEUSD", "AVAXUSD", "DOTUSD", "LINKUSD",
    "MATICUSD", "LTCUSD", "TRXUSD", "UNIUSD", "BCHUSD",
    "ETCUSD", "XLMUSD", "NEARUSD", "FILUSD", "ICPUSD"
]

# ----------------- تابع گرفتن کندل‌ها -----------------
def get_candles(symbol):
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol,
        "interval": "15min",
        "apikey": ALPHA_VANTAGE_API_KEY,
        "outputsize": "compact"
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        time_series = data.get("Time Series (15min)")
        if time_series is None:
            print(f"خطا در دریافت داده‌های {symbol}: {data}")
            return None
        df = pd.DataFrame.from_dict(time_series, orient='index')
        df.rename(columns={
            "1. open": "open",
            "2. high": "high",
            "3. low": "low",
            "4. close": "close",
            "5. volume": "volume"
        }, inplace=True)
        df = df.astype(float)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        return df
    except Exception as e:
        print(f"خطا در دریافت داده‌های {symbol}: {e}")
        return None

# ----------------- تابع سیگنال‌گیری -----------------
def get_signal(symbol):
    df = get_candles(symbol)
    if df is None or len(df) < 20:
        return f"⚠️ داده کافی برای {symbol} موجود نیست."

    close = df["close"]

    rsi = RSIIndicator(close).rsi().iloc[-1]
    macd = MACD(close).macd_diff().iloc[-1]
    ema_fast = EMAIndicator(close, window=9).ema_indicator().iloc[-1]
    ema_slow = EMAIndicator(close, window=21).ema_indicator().iloc[-1]
    adx = ADXIndicator(df["high"], df["low"], close).adx().iloc[-1]
    stoch = StochasticOscillator(df["high"], df["low"], close).stoch_signal().iloc[-1]

    count_long = 0
    count_short = 0

    if rsi > 60: count_long += 1
    elif rsi < 40: count_short += 1

    if macd > 0: count_long += 1
    elif macd < 0: count_short += 1

    if ema_fast > ema_slow: count_long += 1
    else: count_short += 1

    if adx > 25: count_long += 1
    else: count_short += 1

    if stoch > 70: count_short += 1
    elif stoch < 30: count_long += 1

    if count_long >= 3:
        return f"📈 {symbol}: LONG ({count_long}/5)"
    elif count_short >= 3:
        return f"📉 {symbol}: SHORT ({count_short}/5)"
    else:
        return f"⚪ {symbol}: NEUTRAL"

# ----------------- مدیریت اجرای ربات -----------------
running = False
sent_signals = {}  # ذخیره سیگنال‌های ارسال شده قبلی برای جلوگیری از تکرار

def start(update, context):
    global running
    if not running:
        running = True
        context.bot.send_message(chat_id=update.effective_chat.id, text="✅ ربات فعال شد.")
        threading.Thread(target=run_bot).start()
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="ربات از قبل فعاله.")

def stop(update, context):
    global running
    running = False
    context.bot.send_message(chat_id=update.effective_chat.id, text="⛔ ربات متوقف شد.")

# ----------------- اجرای اصلی ربات -----------------
def run_bot():
    while running:
        for symbol in symbols:
            signal = get_signal(symbol)
            # فقط اگر LONG یا SHORT با حداقل 3 تایید بود ارسال کن و اگر قبلا ارسال نشده بود
            if "LONG" in signal or "SHORT" in signal:
                count = int(signal.split("(")[1].split("/")[0])
                if count >= 3:
                    if sent_signals.get(symbol) != signal:
                        sent_signals[symbol] = signal
                        try:
                            updater.bot.send_message(chat_id=CHAT_ID, text=signal)
                            updater.bot.send_message(chat_id=CHANNEL_ID, text=signal)
                        except Exception as e:
                            print(f"خطا در ارسال پیام برای {symbol}: {e}")
            else:
                # سیگنال خنثی رو پاک می‌کنیم
                sent_signals[symbol] = None

            time.sleep(1)  # بین هر ارز 1 ثانیه فاصله

        time.sleep(60)  # هر 1 دقیقه کل چرخه تکرار

# ----------------- راه‌اندازی تلگرام و Flask -----------------
updater = Updater(BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("stop", stop))

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask).start()
updater.start_polling()
