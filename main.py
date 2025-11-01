import os
import logging
import mimetypes
import requests
import time
from urllib.parse import urlparse
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی از فایل .env
load_dotenv()

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن ربات تلگرام از فایل .env یا مقدار پیش‌فرض
BOT_TOKEN = os.getenv('BOT_TOKEN', '8289666254:AAEIvyX0orV6tijM1ATjt_qHppICiNXxOlc')
API_ID = os.getenv('API_ID', '2040')
API_HASH = os.getenv('API_HASH', 'b18441a1ff607e10a989891a5462e627')

# پوشه موقت برای ذخیره فایل‌ها
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیام خوش‌آمدگویی"""
    welcome_message = (
        "سلام! 👋\n\n"
        "من یک ربات دانلود و ارسال فایل هستم.\n\n"
        "کافیست لینک دانلود فایل را برای من ارسال کنید.\n"
        "من فایل را دانلود کرده و برای شما ارسال می‌کنم.\n\n"
        "📹 فایل‌های ویدیویی به صورت ویدیو\n"
        "📄 سایر فایل‌ها به صورت سند\n\n"
        "برای شروع، یک لینک دانلود ارسال کنید!"
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنمای استفاده"""
    help_text = (
        "📖 راهنمای استفاده:\n\n"
        "1️⃣ لینک دانلود فایل را ارسال کنید\n"
        "2️⃣ صبر کنید تا فایل دانلود شود\n"
        "3️⃣ فایل برای شما ارسال می‌شود\n\n"
        "✅ بدون محدودیت حجم فایل\n\n"
        "دستورات:\n"
        "/start - شروع\n"
        "/help - راهنما"
    )
    await update.message.reply_text(help_text)


def is_valid_url(url: str) -> bool:
    """بررسی معتبر بودن URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def get_file_extension_from_url(url: str, content_type: str = None) -> str:
    """استخراج پسوند فایل از URL یا Content-Type"""
    # ابتدا از URL استخراج کنیم
    parsed_url = urlparse(url)
    path = parsed_url.path
    if path:
        ext = os.path.splitext(path)[1]
        if ext:
            return ext
    
    # اگر از URL نشد، از Content-Type استفاده کنیم
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(';')[0].strip())
        if ext:
            return ext
    
    return ""


def is_video_file(filename: str, content_type: str = None) -> bool:
    """تشخیص اینکه فایل ویدیو است یا خیر"""
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpeg', '.mpg']
    
    # بررسی پسوند فایل
    ext = os.path.splitext(filename)[1].lower()
    if ext in video_extensions:
        return True
    
    # بررسی Content-Type
    if content_type and content_type.startswith('video/'):
        return True
    
    return False


def create_progress_bar(percentage: float, length: int = 10) -> str:
    """ایجاد نوار پیشرفت"""
    filled = int(length * percentage / 100)
    bar = '█' * filled + '░' * (length - filled)
    return bar


async def download_file(url: str, filename: str, status_message=None) -> tuple:
    """دانلود فایل از URL با نمایش پیشرفت"""
    try:
        # ارسال درخواست HEAD برای دریافت اطلاعات فایل
        head_response = requests.head(url, allow_redirects=True, timeout=10)
        content_type = head_response.headers.get('content-type', '')
        total_size = int(head_response.headers.get('content-length', 0))
        
        # تعیین نام فایل با پسوند مناسب
        if not os.path.splitext(filename)[1]:
            ext = get_file_extension_from_url(url, content_type)
            filename = filename + ext
        
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        
        # دانلود فایل با نمایش پیشرفت
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        downloaded_size = 0
        last_update_time = time.time()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # به‌روزرسانی نوار پیشرفت هر 2 ثانیه
                    current_time = time.time()
                    if total_size > 0 and status_message:
                        percentage = (downloaded_size / total_size) * 100
                        
                        # آپدیت هر 2 ثانیه یا در پایان دانلود
                        if current_time - last_update_time >= 2 or percentage >= 100:
                            progress_bar = create_progress_bar(percentage)
                            downloaded_mb = downloaded_size / (1024 * 1024)
                            total_mb = total_size / (1024 * 1024)
                            
                            try:
                                await status_message.edit_text(
                                    f"⏬ در حال دانلود...\n\n"
                                    f"{progress_bar} {percentage:.1f}%\n\n"
                                    f"📦 {downloaded_mb:.2f} MB / {total_mb:.2f} MB"
                                )
                                last_update_time = current_time
                            except Exception:
                                # اگر خطای Rate Limit بود، نادیده بگیر
                                pass
        
        return filepath, content_type, total_size
    
    except requests.exceptions.RequestException as e:
        logger.error(f"خطا در دانلود فایل: {e}")
        return None, f"❌ خطا در دانلود فایل: {str(e)}", 0
    except Exception as e:
        logger.error(f"خطای غیرمنتظره: {e}")
        return None, f"❌ خطای غیرمنتظره: {str(e)}", 0


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش پیام‌های دریافتی"""
    message_text = update.message.text.strip()
    
    # بررسی اینکه پیام یک URL است
    if not is_valid_url(message_text):
        await update.message.reply_text(
            "❌ لطفاً یک لینک معتبر ارسال کنید.\n"
            "مثال: https://example.com/file.mp4"
        )
        return
    
    # ارسال پیام در حال دانلود
    status_message = await update.message.reply_text("⏳ در حال دانلود فایل...")
    
    try:
        # دانلود فایل
        url = message_text
        filename = f"file_{update.message.message_id}"
        
        filepath, result, total_size = await download_file(url, filename, status_message)
        
        if filepath is None:
            await status_message.edit_text(result)
            return
        
        content_type = result
        
        # بررسی حجم فایل
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)
        
        # آپدیت پیام وضعیت
        await status_message.edit_text(
            f"✅ دانلود کامل شد!\n"
            f"📦 حجم: {file_size_mb:.2f} MB\n"
            f"⏫ در حال ارسال..."
        )
        
        # ارسال فایل
        with open(filepath, 'rb') as f:
            if is_video_file(filepath, content_type):
                # ارسال به صورت ویدیو
                await update.message.reply_video(
                    video=f,
                    caption=f"📹 ویدیو دانلود شده\n📦 حجم: {file_size_mb:.2f} MB",
                    supports_streaming=True
                )
            else:
                # ارسال به صورت سند
                await update.message.reply_document(
                    document=f,
                    caption=f"📄 فایل دانلود شده\n📦 حجم: {file_size_mb:.2f} MB"
                )
        
        # حذف پیام وضعیت
        await status_message.delete()
        
        # حذف فایل موقت
        os.remove(filepath)
        logger.info(f"فایل {filepath} با موفقیت ارسال و حذف شد.")
    
    except Exception as e:
        logger.error(f"خطا در پردازش فایل: {e}")
        await status_message.edit_text(f"❌ خطا در پردازش فایل: {str(e)}")
        
        # حذف فایل در صورت خطا
        if filepath and os.path.exists(filepath):
            os.remove(filepath)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت خطاها"""
    logger.error(f"خطا: {context.error}")
    if update and update.message:
        await update.message.reply_text("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")


def main():
    """تابع اصلی برای اجرای ربات"""
    # بررسی توکن
    if not BOT_TOKEN:
        print("❌ توکن ربات یافت نشد!")
        print("لطفاً فایل .env را بررسی کنید یا توکن را در کد تنظیم کنید.")
        return
    
    print(f"✅ توکن ربات بارگذاری شد")
    print(f"🔑 API ID: {API_ID}")
    
    # شروع Flask server برای keep-alive (برای Render.com)
    try:
        from keep_alive import keep_alive
        keep_alive()
        print("🌐 Flask server برای keep-alive راه‌اندازی شد")
    except ImportError:
        print("⚠️ keep_alive.py یافت نشد - در حالت عادی اجرا می‌شود")
    
    # ساخت Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # اضافه کردن هندلر خطا
    application.add_error_handler(error_handler)
    
    # شروع ربات
    print("🤖 ربات در حال اجرا است...")
    print("برای توقف ربات از Ctrl+C استفاده کنید.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
