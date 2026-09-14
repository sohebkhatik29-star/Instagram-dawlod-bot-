import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Telegram API credentials from https://my.telegram.org
API_ID   = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")

# Telegram Bot Token from @BotFather
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    print("⚠️ WARNING: BOT_TOKEN is not set yet. Set BOT_TOKEN in .env or environment variables.")

# Owner & Sudo Configuration
OWNER_USERNAMES   = ["movies_1780"]
OWNER_IDS         = [int(x) for x in os.environ.get("OWNER_IDS", "").split(",") if x.strip().isdigit()]
SUDO_USERS        = [int(x) for x in os.environ.get("SUDO_USERS", "").split(",") if x.strip().isdigit()]

# Official Channels & Branding for @movies_1780
FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "MoviesGroupG3")
UPDATE_CHANNEL_URL = os.environ.get("UPDATE_CHANNEL_URL", "https://t.me/MoviesGroupG3")
OWNER_LINK        = os.environ.get("OWNER_LINK", "https://t.me/movies_1780")
BOT_NAME          = os.environ.get("BOT_NAME", "Ash Insta Downloader Bot")
DOWNLOAD_DIR      = os.environ.get("DOWNLOAD_DIR", "downloads")
DATABASE_FILE     = os.environ.get("DATABASE_FILE", "bot_database.db")
PORT              = int(os.environ.get("PORT", "8080"))

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
