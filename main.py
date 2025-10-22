import os
import logging
import yt_dlp
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("🎵 TikTok Downloader Bot Started!")

# ===== CONFIGURATION =====
BOT_TOKEN = os.getenv("BOT_TOKEN")

class TikTokDownloader:
    def __init__(self):
        self.ydl_opts = {
            'format': 'best',
            'outtmpl': '/tmp/%(title).100s.%(ext)s',
            'quiet': False,
        }
    
    def is_tiktok_url(self, url):
        tiktok_domains = [
            'tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com',
            'www.tiktok.com', 'm.tiktok.com'
        ]
        try:
            parsed = urlparse(url)
            return any(domain in parsed.netloc for domain in tiktok_domains)
        except:
            return False
    
    def download_tiktok_video(self, url):
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'tiktok_video')[:100]
                duration = info.get('duration', 0)
                
                if duration > 180:
                    return None, "Video too long (max 3 minutes)"
                
                ydl.download([url])
                
                for file in os.listdir('/tmp'):
                    if file.endswith('.mp4'):
                        return f"/tmp/{file}", title
                
                return None, "File not found"
                
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None, f"Download failed: {str(e)}"
    
    def cleanup_file(self, file_path):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass

downloader = TikTokDownloader()

def start_command(update: Update, context: CallbackContext):
    welcome_text = """
🎵 **TikTok Video Downloader Bot**

Send me any TikTok URL and I'll download the video for you!

**Supported URLs:**
• tiktok.com/...
• vm.tiktok.com/...
• vt.tiktok.com/...

**Running on:** ☁️ Cloud (24/7)
    """
    update.message.reply_text(welcome_text)

def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text
    
    if not downloader.is_tiktok_url(user_message):
        update.message.reply_text("❌ Please send a valid TikTok URL")
        return
    
    processing_msg = update.message.reply_text("⏬ Downloading your TikTok video...")
    
    try:
        file_path, video_title = downloader.download_tiktok_video(user_message.strip())
        
        if file_path and os.path.exists(file_path):
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            
            if file_size > 50:
                processing_msg.edit_text("❌ Video too large (max 50MB)")
                downloader.cleanup_file(file_path)
                return
            
            with open(file_path, 'rb') as video_file:
                update.message.reply_video(
                    video=video_file,
                    caption=f"🎵 {video_title}\n✅ Downloaded via Cloud Bot"
                )
            
            processing_msg.edit_text("✅ Video sent successfully!")
            downloader.cleanup_file(file_path)
            
        else:
            processing_msg.edit_text(f"❌ {video_title}")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        processing_msg.edit_text("❌ Download failed. Try again.")

def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Error: {context.error}")

def main():
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN not set!")
        return
    
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(MessageHandler(Filters.text, handle_message))
    dp.add_error_handler(error_handler)
    
    logger.info("🤖 Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
