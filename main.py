import os
import logging
import mimetypes
import requests
import time
import yt_dlp
from urllib.parse import urlparse
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from dotenv import load_dotenv
from pyrogram import Client
import asyncio

# بارگذاری متغیرهای محیطی از فایل .env
load_dotenv()

# تنظیمات پراکسی برای PythonAnywhere (اختیاری)
PROXY_URL = os.getenv('PROXY_URL', None)  # مثال: http://proxy.server:3128
# اگر می‌خواهید دانلود فایل هم از طریق پراکسی انجام شود (در صورتی که هاست مقصد در whitelist باشد) این را true کنید
ALLOW_DOWNLOAD_VIA_PROXY = os.getenv('ALLOW_DOWNLOAD_VIA_PROXY', 'false').strip().lower() in ('1','true','yes','on')
# اگر روی هاستی هستید که outbound محدود است (مثل PythonAnywhere Free)، دانلود محلی را غیرفعال کنید
DIRECT_SEND_ONLY = os.getenv('DIRECT_SEND_ONLY', 'false').strip().lower() in ('1','true','yes','on')

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن ربات تلگرام از فایل .env (بدون مقدار پیش‌فرض برای امنیت)
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')

# پوشه موقت برای ذخیره فایل‌ها
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ایجاد Pyrogram client برای فایل‌های بزرگ (بیشتر از 50MB)
pyrogram_client = None

def get_pyrogram_client():
    """ایجاد یا برگرداندن Pyrogram client"""
    global pyrogram_client
    if pyrogram_client is None and API_ID and API_HASH and BOT_TOKEN:
        pyrogram_client = Client(
            "file_downloader_bot",
            api_id=int(API_ID),
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workdir=DOWNLOAD_FOLDER
        )
    return pyrogram_client

# نکته: پراکسی فقط برای Telegram Bot API استفاده می‌شود
# برای دانلود فایل‌ها از پراکسی استفاده نمی‌کنیم تا محدودیت whitelist نداشته باشیم


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیام خوش‌آمدگویی"""
    welcome_message = (
        "سلام! 👋\n\n"
        "من یک ربات دانلود و ارسال فایل هستم.\n\n"
        "🎬 دانلود از سایت‌های ویدیویی:\n"
        "• YouTube, Vimeo, Dailymotion\n"
        "• Pornhub, Xvideos, Xnxx\n"
        "• Twitter, Instagram, TikTok\n"
        "• و بیش از 1000 سایت دیگر!\n\n"
        "📥 دانلود فایل مستقیم:\n"
        "• هر لینک دانلود مستقیم\n\n"
        "📹 ویدیوها به صورت ویدیو\n"
        "📄 سایر فایل‌ها به صورت سند\n\n"
        "برای شروع، یک لینک ارسال کنید!"
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنمای استفاده"""
    help_text = (
        "📖 راهنمای استفاده:\n\n"
        "🎬 دانلود از سایت‌های ویدیویی:\n"
        "فقط لینک صفحه ویدیو را ارسال کنید\n"
        "مثال: https://www.youtube.com/watch?v=...\n\n"
        "📥 دانلود فایل مستقیم:\n"
        "لینک دانلود مستقیم فایل را ارسال کنید\n"
        "مثال: https://example.com/file.zip\n\n"
        "✅ بدون محدودیت حجم فایل\n"
        "✅ پشتیبانی از 1000+ سایت\n\n"
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


def is_video_site(url: str) -> bool:
    """بررسی اینکه URL از سایت‌های ویدیویی است"""
    video_sites = [
        'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com',
        'xvideos.com', 'pornhub.com', 'xnxx.com', 'redtube.com',
        'xhamster.com', 'spankbang.com', 'eporner.com', 'youporn.com',
        'twitter.com', 'x.com', 'instagram.com', 'tiktok.com',
        'facebook.com', 'twitch.tv', 'reddit.com'
    ]
    url_lower = url.lower()
    return any(site in url_lower for site in video_sites)


async def download_video_ytdlp(url: str, status_message=None) -> tuple:
    """دانلود ویدیو با yt-dlp از سایت‌های مختلف"""
    try:
        # تنظیمات yt-dlp
        output_template = os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s')
        
        ydl_opts = {
            'format': 'best[height<=720]/best',  # کیفیت 720p یا بهترین موجود (حداکثر 2GB با Pyrogram)
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        # اگر پراکسی تنظیم شده و مجاز است
        if PROXY_URL and ALLOW_DOWNLOAD_VIA_PROXY:
            ydl_opts['proxy'] = PROXY_URL
        
        last_update_time = [time.time()]  # استفاده از list برای mutable در nested function
        
        def progress_hook(d):
            """نمایش پیشرفت دانلود"""
            if d['status'] == 'downloading' and status_message:
                current_time = time.time()
                if current_time - last_update_time[0] >= 2:
                    try:
                        downloaded = d.get('downloaded_bytes', 0)
                        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                        
                        if total > 0:
                            percentage = (downloaded / total) * 100
                            progress_bar = create_progress_bar(percentage)
                            downloaded_mb = downloaded / (1024 * 1024)
                            total_mb = total / (1024 * 1024)
                            speed = d.get('speed', 0)
                            speed_mb = speed / (1024 * 1024) if speed else 0
                            
                            import asyncio
                            asyncio.create_task(status_message.edit_text(
                                f"⏬ در حال دانلود ویدیو...\n\n"
                                f"{progress_bar} {percentage:.1f}%\n\n"
                                f"📦 {downloaded_mb:.2f} MB / {total_mb:.2f} MB\n"
                                f"⚡ سرعت: {speed_mb:.2f} MB/s"
                            ))
                        else:
                            downloaded_mb = downloaded / (1024 * 1024)
                            import asyncio
                            asyncio.create_task(status_message.edit_text(
                                f"⏬ در حال دانلود ویدیو...\n\n"
                                f"📦 {downloaded_mb:.2f} MB"
                            ))
                        
                        last_update_time[0] = current_time
                    except Exception:
                        pass
        
        ydl_opts['progress_hooks'] = [progress_hook]
        
        # دانلود ویدیو
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if status_message:
                await status_message.edit_text("🔍 در حال دریافت اطلاعات ویدیو...")
            
            info = ydl.extract_info(url, download=True)
            
            # پیدا کردن فایل دانلود شده
            if 'requested_downloads' in info and info['requested_downloads']:
                filepath = info['requested_downloads'][0]['filepath']
            else:
                # جستجوی فایل در پوشه downloads
                title = info.get('title', 'video')
                ext = info.get('ext', 'mp4')
                filepath = os.path.join(DOWNLOAD_FOLDER, f"{title}.{ext}")
            
            if not os.path.exists(filepath):
                # جستجوی فایل با الگوی مشابه
                import glob
                pattern = os.path.join(DOWNLOAD_FOLDER, f"*{info.get('id', '')}*")
                files = glob.glob(pattern)
                if files:
                    filepath = files[0]
                else:
                    raise FileNotFoundError("فایل دانلود شده یافت نشد")
            
            file_size = os.path.getsize(filepath)
            return filepath, 'video/mp4', file_size
    
    except Exception as e:
        logger.error(f"خطا در دانلود ویدیو با yt-dlp: {e}")
        return None, f"❌ خطا در دانلود ویدیو: {str(e)}", 0


async def download_file(url: str, filename: str, status_message=None) -> tuple:
    """دانلود فایل از URL با نمایش پیشرفت"""
    try:
        # ایجاد session بدون پراکسی برای دانلود فایل
        session = requests.Session()
        session.trust_env = False  # نادیده گرفتن متغیرهای محیطی پراکسی
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119 Safari/537.36',
            'Accept': '*/*',
            'Connection': 'keep-alive',
        })
        proxies = {'http': PROXY_URL, 'https': PROXY_URL} if (PROXY_URL and ALLOW_DOWNLOAD_VIA_PROXY) else None

        # ارسال درخواست HEAD برای دریافت اطلاعات فایل (در صورت امکان)
        content_type = ''
        total_size = 0
        try:
            head_response = session.head(url, allow_redirects=True, timeout=20)
            content_type = head_response.headers.get('content-type', '') or ''
            try:
                total_size = int(head_response.headers.get('content-length', 0) or 0)
            except Exception:
                total_size = 0
        except Exception:
            # برخی سرورها به HEAD پاسخ نمی‌دهند؛ در ادامه از پاسخ GET استفاده می‌کنیم
            pass
        
        # تعیین نام فایل با پسوند مناسب
        if not os.path.splitext(filename)[1]:
            ext = get_file_extension_from_url(url, content_type)
            filename = filename + ext
        
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        
        # دانلود فایل با نمایش پیشرفت (ابتدا مستقیم؛ در صورت نیاز از پراکسی استفاده می‌شود)
        try:
            response = session.get(url, stream=True, timeout=60, allow_redirects=True)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            if proxies:
                try:
                    response = session.get(url, stream=True, timeout=60, allow_redirects=True, proxies=proxies)
                    response.raise_for_status()
                except requests.exceptions.RequestException:
                    # اگر با پراکسی هم نشد، همان خطای اولیه را گزارش کن
                    raise e
            else:
                # تلاش با HTTP به جای HTTPS در صورت خطای اتصال
                if url.startswith('https://'):
                    url_http = 'http://' + url[8:]
                    try:
                        response = session.get(url_http, stream=True, timeout=60, allow_redirects=True)
                        response.raise_for_status()
                        url = url_http  # برای ادامه پردازش
                    except requests.exceptions.RequestException:
                        raise e
                else:
                    raise e

        # به‌روزرسانی اطلاعات از پاسخ GET در صورت نیاز
        if not content_type:
            content_type = response.headers.get('content-type', '') or ''
        if total_size == 0:
            try:
                total_size = int(response.headers.get('content-length', 0) or 0)
            except Exception:
                total_size = 0
        
        downloaded_size = 0
        last_update_time = time.time()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # به‌روزرسانی نوار پیشرفت هر 2 ثانیه
                    current_time = time.time()
                    if status_message:
                        if total_size > 0:
                            percentage = (downloaded_size / total_size) * 100
                        else:
                            percentage = None
                        
                        # آپدیت هر 2 ثانیه یا در پایان دانلود
                        if current_time - last_update_time >= 2 or (percentage is not None and percentage >= 100):
                            downloaded_mb = downloaded_size / (1024 * 1024)
                            try:
                                if percentage is not None:
                                    progress_bar = create_progress_bar(percentage)
                                    total_mb = total_size / (1024 * 1024)
                                    await status_message.edit_text(
                                        f"⏬ در حال دانلود...\n\n"
                                        f"{progress_bar} {percentage:.1f}%\n\n"
                                        f"📦 {downloaded_mb:.2f} MB / {total_mb:.2f} MB"
                                    )
                                else:
                                    await status_message.edit_text(
                                        f"⏬ در حال دانلود...\n\n"
                                        f"📦 {downloaded_mb:.2f} MB"
                                    )
                                last_update_time = current_time
                            except Exception:
                                # اگر خطای Rate Limit بود، نادیده بگیر
                                pass
        
        return filepath, content_type, total_size
    
    except requests.exceptions.RequestException as e:
        logger.error(f"خطا در دانلود فایل: {e}")
        friendly = str(e)
        if 'Connection refused' in friendly or 'Errno 111' in friendly:
            friendly = "اتصال به سرور فایل برقرار نشد (احتمالاً توسط هاست/فایروال مسدود شده است)."
        return None, f"❌ خطا در دانلود فایل: {friendly}", 0
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
    
    # پیام وضعیت
    status_message = await update.message.reply_text("⏳ در حال پردازش...")
    
    try:
        url = message_text
        filename = f"file_{update.message.message_id}"
        
        # بررسی اینکه آیا از سایت‌های ویدیویی است
        if is_video_site(url):
            # استفاده از yt-dlp برای دانلود ویدیو
            if DIRECT_SEND_ONLY:
                await status_message.edit_text(
                    "❌ دانلود ویدیو از این سایت در محیط محدود امکان‌پذیر نیست.\n"
                    "لطفاً متغیر DIRECT_SEND_ONLY را غیرفعال کنید."
                )
                return
            
            await status_message.edit_text("🎬 شناسایی سایت ویدیویی - استفاده از yt-dlp...")
            filepath, result, total_size = await download_video_ytdlp(url, status_message)
        else:
            # تلاش برای ارسال مستقیم توسط سرورهای تلگرام (بدون دانلود محلی)
            try:
                await status_message.edit_text("⏳ تلاش برای ارسال مستقیم توسط تلگرام...")
                if is_video_file(url):
                    await update.message.reply_video(
                        video=url,
                        caption="📹 ویدیو (ارسال مستقیم توسط تلگرام)",
                        supports_streaming=True
                    )
                else:
                    await update.message.reply_document(
                        document=url,
                        caption="📄 فایل (ارسال مستقیم توسط تلگرام)"
                    )
                await status_message.delete()
                return
            except Exception as direct_send_error:
                logger.warning(f"ارسال مستقیم توسط تلگرام ناکام ماند: {direct_send_error}")
                # اگر در محیط محدود هستیم، دانلود محلی را انجام ندهیم
                if DIRECT_SEND_ONLY:
                    await status_message.edit_text(
                        "❌ ارسال مستقیم توسط تلگرام ناموفق بود و دانلود محلی در این محیط مجاز نیست.\n"
                        "لطفاً لینک دیگری ارسال کنید یا متغیر DIRECT_SEND_ONLY را غیرفعال کنید."
                    )
                    return
                await status_message.edit_text("⏬ دانلود محلی آغاز شد...")

            # دانلود محلی با نوار پیشرفت
            filepath, result, total_size = await download_file(url, filename, status_message)
        
        if filepath is None:
            await status_message.edit_text(result)
            return
        
        content_type = result
        
        # بررسی حجم فایل
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)
        
        # بررسی محدودیت 2 گیگابایت (با Pyrogram)
        if file_size_mb > 2000:
            await status_message.edit_text(
                f"❌ فایل خیلی بزرگه! ({file_size_mb:.2f} MB = {file_size_mb/1024:.2f} GB)\n\n"
                f"حداکثر سایز مجاز ۲ گیگابایت هست.\n"
                f"لطفاً ویدیو با کیفیت پایین‌تر یا فایل کوچک‌تر ارسال کنید."
            )
            os.remove(filepath)
            return
        
        # آپدیت پیام وضعیت
        await status_message.edit_text(
            f"✅ دانلود کامل شد!\n"
            f"📦 حجم: {file_size_mb:.2f} MB\n"
            f"⏫ در حال ارسال..."
        )
        
        # انتخاب روش ارسال بر اساس سایز فایل
        if file_size_mb > 50:
            # استفاده از Pyrogram برای فایل‌های بزرگ (50MB تا 2GB)
            await status_message.edit_text(
                f"✅ دانلود کامل شد!\n"
                f"📦 حجم: {file_size_mb:.2f} MB\n"
                f"⏫ در حال ارسال (Pyrogram برای فایل بزرگ)..."
            )
            
            try:
                client = get_pyrogram_client()
                if client:
                    await client.start()
                    
                    # دریافت chat_id از update
                    chat_id = update.message.chat_id
                    
                    if is_video_file(filepath, content_type):
                        # ارسال ویدیو
                        await client.send_video(
                            chat_id=chat_id,
                            video=filepath,
                            caption=f"📹 ویدیو دانلود شده\n📦 حجم: {file_size_mb:.2f} MB",
                            supports_streaming=True
                        )
                    else:
                        # ارسال سند
                        await client.send_document(
                            chat_id=chat_id,
                            document=filepath,
                            caption=f"📄 فایل دانلود شده\n📦 حجم: {file_size_mb:.2f} MB"
                        )
                    
                    await client.stop()
                    logger.info(f"فایل بزرگ {filepath} با Pyrogram ارسال شد")
                else:
                    raise Exception("Pyrogram client موجود نیست")
            except Exception as e:
                logger.error(f"خطا در ارسال با Pyrogram: {e}")
                raise
        else:
            # استفاده از Bot API معمولی برای فایل‌های کوچک (زیر 50MB)
            with open(filepath, 'rb') as f:
                if is_video_file(filepath, content_type):
                    # ارسال به صورت ویدیو
                    await update.message.reply_video(
                        video=f,
                        caption=f"📹 ویدیو دانلود شده\n📦 حجم: {file_size_mb:.2f} MB",
                        supports_streaming=True,
                        read_timeout=300,
                        write_timeout=300,
                        connect_timeout=30,
                        pool_timeout=30
                    )
                else:
                    # ارسال به صورت سند
                    await update.message.reply_document(
                        document=f,
                        caption=f"📄 فایل دانلود شده\n📦 حجم: {file_size_mb:.2f} MB",
                        read_timeout=300,
                        write_timeout=300,
                        connect_timeout=30,
                        pool_timeout=30
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
    
    # ساخت Application با پشتیبانی از پراکسی و تایم‌اوت بالا برای آپلود فایل‌های بزرگ
    app_builder = Application.builder().token(BOT_TOKEN)
    
    # تنظیم HTTPXRequest با تایم‌اوت بالا برای آپلود فایل‌های بزرگ
    from telegram.request import HTTPXRequest
    request_kwargs = {
        'connection_pool_size': 8,
        'connect_timeout': 30.0,
        'read_timeout': 300.0,
        'write_timeout': 300.0,
        'pool_timeout': 30.0
    }
    
    # اگر پراکسی تنظیم شده، به تنظیمات اضافه کن
    if PROXY_URL:
        request_kwargs['proxy_url'] = PROXY_URL
        print(f"🌐 پراکسی برای Telegram Bot تنظیم شد: {PROXY_URL}")
    
    request = HTTPXRequest(**request_kwargs)
    app_builder.request(request)
    print(f"✅ تایم‌اوت برای آپلود فایل‌های بزرگ تنظیم شد (300 ثانیه)")
    
    application = app_builder.build()
    
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
