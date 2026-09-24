import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Telegram API credentials from https://my.telegram.org
API_ID   = int(os.environ.get("API_ID", "30720676"))
API_HASH = os.environ.get("API_HASH", "a078e3476750afbd6db7d6c5e5e658d9")

# Telegram Bot Token from @BotFather
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8787823232:AAGH7QPCSvgV_nJ2Hi-9XasY-3yjm6mvHDc")
if not BOT_TOKEN:
    print("⚠️ WARNING: BOT_TOKEN is not set yet. Set BOT_TOKEN in .env or environment variables.")

# Owner & Sudo Configuration
OWNER_USERNAMES   = [x.strip().replace("@", "") for x in os.environ.get("OWNER_USERNAMES", "movies_1780").split(",") if x.strip()]
_env_owner_ids    = [int(x) for x in os.environ.get("OWNER_IDS", "5566977478").split(",") if x.strip().isdigit()]
if 5566977478 not in _env_owner_ids:
    _env_owner_ids.append(5566977478)
OWNER_IDS         = _env_owner_ids
SUDO_USERS        = [int(x) for x in os.environ.get("SUDO_USERS", "").split(",") if x.strip().isdigit()]

# Official Channels & Branding
FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "MoviesGroupG3")
UPDATE_CHANNEL_URL = os.environ.get("UPDATE_CHANNEL_URL", "https://t.me/MoviesGroupG3")
SUPPORT_GROUP_URL = os.environ.get("SUPPORT_GROUP_URL", "https://t.me/ash_movie_j")
LOG_CHANNEL_ID    = int(os.environ.get("LOG_CHANNEL_ID", "-1004350432978"))
BOT_NAME          = os.environ.get("BOT_NAME", "Ash Insta Downloader Bot")
START_PHOTO_URL   = os.environ.get("START_PHOTO_URL", "https://d.uguu.se/GKqJNpbg.jpg")
START_PIC_PATH    = os.path.join(os.path.dirname(__file__), "assets", "start_pic.jpg")
DOWNLOAD_DIR      = os.environ.get("DOWNLOAD_DIR", "downloads")
DATABASE_FILE     = os.environ.get("DATABASE_FILE", "bot_database.db")
PORT              = int(os.environ.get("PORT", "8080"))

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
