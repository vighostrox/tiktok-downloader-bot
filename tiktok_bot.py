import os
import logging
import requests
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("🎵 TikTok Downloader Bot Started!")

# ===== CONFIGURATION =====
BOT_TOKEN = "8216411154:AAGgVMkiwfRS-sgBYowZ1UvWRB6u-ci5eH4"  # Get from @BotFather

class TikTokDownloader:
    def __init__(self):
        self.ydl_opts = {
            'format': 'best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
        }
        
        # Create downloads directory
        os.makedirs('downloads', exist_ok=True)
    
    def is_tiktok_url(self, url):
        """Check if URL is from TikTok"""
        tiktok_domains = [
            'tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com',
            'www.tiktok.com', 'm.tiktok.com'
        ]
        parsed = urlparse(url)
        return any(domain in parsed.netloc for domain in tiktok_domains)
    
    def download_tiktok_video(self, url):
        """Download TikTok video"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                # Get video info
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'tiktok_video')
                duration = info.get('duration', 0)
                
                # Check if video is too long (Telegram has 3 minute limit for some bots)
                if duration > 180:  # 3 minutes limit
                    return None, "Video too long (max 3 minutes)"
                
                # Download the video
                ydl.download([url])
                
                # Find the downloaded file
                filename = f"downloads/{title}.mp4"
                if os.path.exists(filename):
                    return filename, title
                else:
                    # Try to find the actual file
                    for file in os.listdir('downloads'):
                        if file.endswith('.mp4'):
                            return f"downloads/{file}", title
                    
                    return None, "Downloaded file not found"
                    
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None, f"Download failed: {str(e)}"
    
    def cleanup_file(self, file_path):
        """Clean up downloaded file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

# Initialize downloader
downloader = TikTokDownloader()

# ===== BOT HANDLERS =====
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    welcome_text = """
🎵 **TikTok Video Downloader Bot**

**How to use:**
1. Send me any TikTok video URL
2. I'll download and send you the video
3. Max video length: 3 minutes

**Supported URLs:**
• tiktok.com/...
• vm.tiktok.com/...
• vt.tiktok.com/...

**Commands:**
/start - Show this help
/help - Get assistance
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = """
🤖 **Need Help?**

**Just send me a TikTok URL and I'll download the video for you!**

**Examples of supported URLs:**
• https://www.tiktok.com/@username/video/123456789
• https://vm.tiktok.com/ABC123/
• https://vt.tiktok.com/XYZ789/

**Features:**
✅ HD quality videos
✅ Fast download
✅ Automatic cleanup
✅ Free to use

**Limitations:**
❌ Max 3 minutes per video
❌ TikTok links only
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    user_message = update.message.text
    
    # Check if message contains a URL
    if not any(domain in user_message for domain in ['tiktok.com', 'vm.', 'vt.']):
        await update.message.reply_text("❌ Please send a valid TikTok URL")
        return
    
    # Extract URL from message
    url = user_message.strip()
    
    # Validate TikTok URL
    if not downloader.is_tiktok_url(url):
        await update.message.reply_text("❌ That doesn't look like a TikTok URL. Please send a valid TikTok video link.")
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text("⏬ Downloading your TikTok video...")
    
    try:
        # Download the video
        file_path, video_title = downloader.download_tiktok_video(url)
        
        if file_path and os.path.exists(file_path):
            # Get file size
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
            
            # Check file size (Telegram limit is 50MB for bots)
            if file_size > 50:
                await processing_msg.edit_text("❌ Video is too large to send via Telegram (max 50MB)")
                downloader.cleanup_file(file_path)
                return
            
            # Send the video
            await update.message.reply_video(
                video=open(file_path, 'rb'),
                caption=f"🎵 **{video_title}**\n\n✅ Downloaded via TikTok Bot",
                parse_mode='Markdown'
            )
            
            # Update processing message
            await processing_msg.edit_text("✅ Video downloaded and sent successfully!")
            
            # Clean up file
            downloader.cleanup_file(file_path)
            
        else:
            await processing_msg.edit_text(f"❌ {video_title}")  # video_title contains error message
            
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        await processing_msg.edit_text("❌ Sorry, I couldn't download that video. Please try again.")
        
        # Clean up any partial files
        try:
            for file in os.listdir('downloads'):
                if file.endswith('.mp4'):
                    os.remove(f"downloads/{file}")
        except:
            pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    try:
        await update.message.reply_text("❌ An error occurred. Please try again later.")
    except:
        pass

# ===== MAIN FUNCTION =====
def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    # Start the bot
    print("🤖 TikTok Downloader Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()