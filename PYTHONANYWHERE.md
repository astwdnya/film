# راهنمای دیپلوی روی PythonAnywhere

## مراحل نصب

### 1. ساخت اکانت
- به [PythonAnywhere.com](https://www.pythonanywhere.com) بروید
- یک اکانت رایگان بسازید

### 2. آپلود فایل‌ها
در بخش **Files**:
- فایل‌های پروژه را آپلود کنید
- یا از Git clone استفاده کنید

### 3. تنظیم پراکسی
1. به **Account** > **API Token** بروید
2. آدرس پراکسی را پیدا کنید (معمولاً: `http://proxy.server:3128`)
3. فایل `.env` را ویرایش کنید:

```env
PROXY_URL=http://proxy.server:3128
```

### 4. نصب کتابخانه‌ها
در **Bash Console**:

```bash
cd ~/your-project-folder
pip3 install --user -r requirements.txt
```

### 5. اجرای ربات
دو روش برای اجرا:

#### روش 1: Always-on Task (توصیه می‌شود)
- به **Tasks** بروید
- یک **Always-on task** بسازید
- دستور: `python3 /home/yourusername/your-project-folder/main.py`

#### روش 2: Bash Console
```bash
python3 main.py
```

**نکته:** در پلن رایگان، فقط یک Always-on task دارید.

## تنظیمات مهم

### پراکسی برای Telegram
کد به صورت هوشمند از پراکسی استفاده می‌کند:
- پراکسی **فقط** برای ارتباط با Telegram Bot API استفاده می‌شود
- دانلود فایل‌ها **بدون پراکسی** انجام می‌شود (برای دسترسی به همه سایت‌ها)
- این روش محدودیت whitelist را دور می‌زند

### Keep-Alive
برای جلوگیری از خاموش شدن:
- Flask server روی پورت 10000 اجرا می‌شود
- از سرویس‌های مانیتور مثل UptimeRobot استفاده کنید
- هر 5 دقیقه به `https://yourusername.pythonanywhere.com/health` درخواست بفرستید

## مشکلات رایج

### خطای "AttributeError: 'Updater' object has no attribute"
این خطا در Python 3.13 رخ می‌دهد. راه‌حل:

```bash
pip uninstall python-telegram-bot -y
pip install python-telegram-bot==21.9 --user
```

یا به صورت یکجا:
```bash
pip uninstall python-telegram-bot -y && pip install python-telegram-bot==21.9 --user
```

### خطای "No module named 'telegram'"
```bash
pip3 install --user python-telegram-bot==21.9
```

### خطای "ProxyError: Tunnel connection failed: 403 Forbidden"
این خطا زمانی رخ می‌دهد که سعی می‌کنید از پراکسی برای دانلود فایل استفاده کنید.

**راه‌حل:** کد به‌روزرسانی شده است و دیگر این مشکل را ندارد:
- پراکسی فقط برای Telegram API استفاده می‌شود
- دانلود فایل‌ها بدون پراکسی انجام می‌شود
- فایل `main.py` جدید را آپلود کنید

### خطای اتصال به Telegram
- مطمئن شوید پراکسی صحیح تنظیم شده
- در PythonAnywhere، فقط whitelist شده سایت‌ها قابل دسترسی هستند
- برای پلن رایگان، ممکن است نیاز به پراکسی باشد

### خطای "Address already in use" یا "Port 10000 is in use"
پورت قبلاً در حال استفاده است. پروسه قبلی را متوقف کنید:

```bash
pkill -f main.py
```

سپس دوباره اجرا کنید:
```bash
python main.py
```

### ربات متوقف می‌شود
- از Always-on task استفاده کنید
- لاگ‌ها را در `/var/log/` بررسی کنید

### نسخه اشتباه نصب می‌شود
اگر pip نسخه 20.7 را به جای 21.9 نصب می‌کند:

```bash
pip uninstall python-telegram-bot httpx -y
pip install --upgrade --force-reinstall python-telegram-bot==21.9 --user
```

## محدودیت‌های پلن رایگان

- ✅ یک Always-on task
- ✅ 512MB فضای دیسک
- ✅ CPU محدود
- ⚠️ فقط whitelist شده سایت‌ها قابل دسترسی
- ⚠️ نیاز به پراکسی برای Telegram

## نکات امنیتی

1. **هرگز توکن را commit نکنید**
2. از فایل `.env` استفاده کنید
3. فایل `.env` را در `.gitignore` قرار دهید

## لینک‌های مفید

- [PythonAnywhere Help](https://help.pythonanywhere.com/)
- [Whitelist Sites](https://www.pythonanywhere.com/whitelist/)
- [Always-on Tasks](https://help.pythonanywhere.com/pages/AlwaysOnTasks/)
