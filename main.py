import time
import requests
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, ADXIndicator

BOT_TOKEN = "7950619090:AAGafe0s5xwEDxXIytd-OFybum3tUCuOZPI"
CHAT_ID = "423311697"
CHANNEL_ID = "-1002876171269"

symbols = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'SOLUSDT', 'DOGEUSDT', 'AVAXUSDT',
    'DOTUSDT', 'MATICUSDT', 'LTCUSDT', 'TRXUSDT', 'SHIBUSDT', 'LINKUSDT', 'UNIUSDT', 'BCHUSDT',
    'XLMUSDT', 'ATOMUSDT', 'ETCUSDT', 'XMRUSDT', 'ICPUSDT', 'NEARUSDT', 'FILUSDT', 'APTUSDT',
    'QNTUSDT', 'IMXUSDT', 'SANDUSDT', 'MANAUSDT', 'THETAUSDT', 'HBARUSDT', 'EGLDUSDT', 'RUNEUSDT',
    'AAVEUSDT', 'GRTUSDT', 'ALGOUSDT', 'AXSUSDT', 'XTZUSDT', 'CHZUSDT', '1INCHUSDT', 'LDOUSDT'
]

active_signals = {}  # symbol: signal info dict
is_running = False
last_update_id = 0
desired_confidence = None  # درصد موفقیت که کاربر می‌خواهد

def telegram_send_message(message, chat_id=CHAT_ID, reply_to=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    if reply_to:
        data["reply_to_message_id"] = reply_to
    try:
        resp = requests.post(url, data=data)
        if resp.ok:
            return resp.json()['result']['message_id']
    except Exception as e:
        print("خطا در ارسال پیام:", e)
    return None

def get_updates():
    global last_update_id
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 20}
    try:
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        if data["ok"]:
            for update in data["result"]:
                last_update_id = update["update_id"]
                if "message" in update and "text" in update["message"]:
                    chat_id = str(update["message"]["chat"]["id"])
                    text = update["message"]["text"].strip().lower()
                    if chat_id == CHAT_ID:
                        handle_command(text)
    except Exception as e:
        print("خطا در دریافت آپدیت:", e)

def handle_command(text):
    global is_running, desired_confidence
    if text == "start":
        if not is_running:
            is_running = True
            desired_confidence = None
            telegram_send_message("✅ ربات فعال شد.\nلطفاً درصد موفقیت سیگنال‌ها را وارد کنید (100، 80، 60، 40، 20 یا all):")
        else:
            telegram_send_message("ربات قبلاً فعال بود.")
    elif text in ["100","80","60","40","20","all"]:
        if is_running and desired_confidence is None:
            text_normalized = convert_to_english_number(text)
            desired_confidence = text_normalized
            telegram_send_message(f"✅ درصد موفقیت روی {desired_confidence}٪ تنظیم شد. تحلیل آغاز می‌شود.")
        else:
            telegram_send_message("❌ ابتدا ربات را با دستور start فعال کنید.")
    elif text == "stop":
        if is_running:
            is_running = False
            desired_confidence = None
            telegram_send_message("⛔ ربات متوقف شد.")
        else:
            telegram_send_message("ربات قبلاً متوقف بود.")
    else:
        telegram_send_message("❌ دستور نامعتبر است. فقط 'start' یا 'stop' بفرست یا درصد موفقیت را وارد کن.")

def convert_to_english_number(text):
    persian_nums = "۰۱۲۳۴۵۶۷۸۹"
    english_nums = "0123456789"
    for p,e in zip(persian_nums, english_nums):
        text = text.replace(p,e)
    return text

def get_binance_klines(symbol, interval='1m', limit=100, retries=3, sleep_between_retries=5):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            if not data:
                raise ValueError("داده‌ای دریافت نشد.")
            return data
        except Exception as e:
            print(f"❌ خطا در دریافت داده‌های {symbol} (تلاش {attempt}): {e}")
            if attempt < retries:
                time.sleep(sleep_between_retries)
            else:
                return None

def analyze_signal(df):
    close = df['close']
    signal_count = 0

    rsi = RSIIndicator(close).rsi().iloc[-1]
    if rsi > 70:
        signal_count += 1  # short
    elif rsi < 30:
        signal_count += 1  # long

    macd = MACD(close).macd_diff().iloc[-1]
    if macd > 0:
        signal_count += 1

    ema_fast = EMAIndicator(close, window=5).ema_indicator().iloc[-1]
    ema_slow = EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    if ema_fast > ema_slow:
        signal_count += 1

    stoch = StochasticOscillator(df['high'], df['low'], close)
    if stoch.stoch().iloc[-1] > stoch.stoch_signal().iloc[-1]:
        signal_count += 1

    adx = ADXIndicator(df['high'], df['low'], close).adx().iloc[-1]
    if adx > 25:
        signal_count += 1

    return signal_count

def calculate_targets(entry, leverage):
    targets = []
    for i in range(1, 9):
        base_target_percent = 10 + (i - 1) * 5
        real_target_percent = base_target_percent / leverage
        target = round(entry * (1 + real_target_percent / 100), 6)
        targets.append((i, target))
    return targets

def calculate_stop_loss(entry, leverage):
    sl_percent = 30 / leverage
    return round(entry * (1 - sl_percent / 100), 6)

def format_duration(seconds):
    mins, sec = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    parts = []
    if hours > 0:
        parts.append(f"{int(hours)} ساعت")
    if mins > 0:
        parts.append(f"{int(mins)} دقیقه")
    if sec > 0:
        parts.append(f"{int(sec)} ثانیه")
    return " و ".join(parts) if parts else "0 ثانیه"

def check_targets_and_stop(symbol, current_price):
    signal = active_signals.get(symbol)
    if not signal:
        return

    entry = signal["entry"]
    leverage = signal["leverage"]
    stop_loss = signal["stop_loss"]
    targets = signal["targets"]
    hit_targets = signal["hit_targets"]
    message_id = signal["message_id"]
    start_time = signal["start_time"]

    # چک حد ضرر
    if current_price <= stop_loss:
        msg = f"❌ {symbol} حد ضرر خورده! قیمت فعلی: {current_price}"
        telegram_send_message(msg, CHANNEL_ID, reply_to=message_id)
        del active_signals[symbol]
        return

    # چک تارگت‌ها
    for i, target in targets:
        if i not in hit_targets and current_price >= target:
            hit_targets.add(i)
            duration_seconds = int(time.time() - start_time)
            duration_text = format_duration(duration_seconds)
            profit_percent = round((target - entry) / entry * 100, 2)
            msg = (f"🎯 تارگت {i} تاچ شد ✅\n"
                   f"⏱ مدت زمان: {duration_text}\n"
                   f"📈 سود: {profit_percent}%")
            telegram_send_message(msg, CHANNEL_ID, reply_to=message_id)

    # اگر همه تارگت‌ها تاچ شده یا سود حداقل 30٪ رسید، سیگنال رو حذف کن (آزاد شدن برای سیگنال جدید)
    if len(hit_targets) == len(targets):
        del active_signals[symbol]
        return

    max_profit = max(((current_price - entry) / entry * 100), 0)
    if max_profit >= 30:
        del active_signals[symbol]

def main():
    global is_running, desired_confidence
    while True:
        get_updates()
        if is_running:
            if desired_confidence is None:
                time.sleep(2)
                continue
            for symbol in symbols:
                if symbol in active_signals:
                    continue

                klines = get_binance_klines(symbol)
                if not klines:
                    continue
                df = pd.DataFrame(klines, columns=[
                    "timestamp", "open", "high", "low", "close", "volume",
                    "close_time", "quote_asset_volume", "number_of_trades",
                    "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
                ])
                df['close'] = df['close'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)

                score = analyze_signal(df)
                confidence = (score / 5) * 100

                if desired_confidence != "all":
                    try:
                        desired_num = int(desired_confidence)
                        if confidence < desired_num:
                            continue
                    except:
                        continue

                if score < 3 or confidence < 30:
                    continue

                leverage = int(confidence // 3.33)
                leverage = min(max(leverage, 10), 30)
                entry = df['close'].iloc[-1]
                targets = calculate_targets(entry, leverage)
                stop_loss = calculate_stop_loss(entry, leverage)

                message = f"🚨 سیگنال LONG برای {symbol}\n"
                message += f"🎯 درصد موفقیت: {int(confidence)}٪\n📈 لوریج: x{leverage}\n💵 قیمت ورود: {entry}\n"
                for i, target in targets:
                    message += f"🎯 تارگت {i}: {target}\n"
                message += f"🛑 حد ضرر: {stop_loss}"

                message_id = telegram_send_message(message, CHANNEL_ID)
                if message_id:
                    active_signals[symbol] = {
                        "entry": entry,
                        "leverage": leverage,
                        "targets": targets,
                        "stop_loss": stop_loss,
                        "message_id": message_id,
                        "hit_targets": set(),
                        "start_time": time.time(),
                    }

            for _ in range(5 * 60 // 5):
                for symbol in list(active_signals.keys()):
                    klines = get_binance_klines(symbol, limit=1)
                    if klines:
                        current_price = float(klines[-1][4])
                        check_targets_and_stop(symbol, current_price)
                    time.sleep(0.1)
                time.sleep(5)
        else:
            print("ربات متوقف است، ۱۰ ثانیه صبر می‌کنم...")
            time.sleep(10)

if __name__ == "__main__":
    main()
