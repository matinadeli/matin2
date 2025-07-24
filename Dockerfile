# استفاده از نسخه پایتون 3.10 رسمی
FROM python:3.10-slim

# تنظیم دایرکتوری کاری داخل کانتینر
WORKDIR /app

# کپی کردن فایل requirements.txt به کانتینر
COPY requirements.txt .

# نصب پکیج‌ها
RUN pip install --no-cache-dir -r requirements.txt

# کپی کل کد پروژه به کانتینر
COPY . .

# اجرای فایل main.py برای شروع ربات
CMD ["python3", "main.py"]
