import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Telegram API credentials from https://my.telegram.org
API_ID   = int(os.environ.get("API_ID") or 30720676)
API_HASH = str(os.environ.get("API_HASH") or "a078e3476750afbd6db7d6c5e5e658d9").strip()

# Telegram Bot Token from @BotFather
BOT_TOKEN = str(os.environ.get("BOT_TOKEN") or "8787823232:AAGH7QPCSvgV_nJ2Hi-9XasY-3yjm6mvHDc").strip()
if not BOT_TOKEN:
    print("⚠️ WARNING: BOT_TOKEN is not set yet.")

# Owner & Sudo Configuration
OWNER_USERNAMES   = [x.strip().replace("@", "") for x in (os.environ.get("OWNER_USERNAMES") or "movies_1780").split(",") if x.strip()]
_raw_owner_ids    = os.environ.get("OWNER_IDS") or "5566977478"
_env_owner_ids    = [int(x) for x in _raw_owner_ids.split(",") if x.strip().isdigit()]
if 5566977478 not in _env_owner_ids:
    _env_owner_ids.append(5566977478)
OWNER_IDS         = _env_owner_ids
SUDO_USERS        = [int(x) for x in (os.environ.get("SUDO_USERS") or "").split(",") if x.strip().isdigit()]

# Official Channels & Branding
FORCE_SUB_CHANNEL = str(os.environ.get("FORCE_SUB_CHANNEL") or "MoviesGroupG3").strip()
UPDATE_CHANNEL_URL = str(os.environ.get("UPDATE_CHANNEL_URL") or "https://t.me/MoviesGroupG3").strip()
SUPPORT_GROUP_URL = str(os.environ.get("SUPPORT_GROUP_URL") or "https://t.me/ash_movie_j").strip()
LOG_CHANNEL_ID    = int(os.environ.get("LOG_CHANNEL_ID") or "-1004350432978")
BOT_NAME          = str(os.environ.get("BOT_NAME") or "Ash Insta Downloader Bot").strip()
START_PHOTO_URL   = str(os.environ.get("START_PHOTO_URL") or "https://d.uguu.se/GKqJNpbg.jpg").strip()
START_PIC_PATH    = os.path.join(os.path.dirname(__file__), "assets", "start_pic.jpg")
DOWNLOAD_DIR      = str(os.environ.get("DOWNLOAD_DIR") or "downloads").strip()
DATABASE_FILE     = str(os.environ.get("DATABASE_FILE") or "bot_database.db").strip()
PORT              = int(os.environ.get("PORT") or "8080")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
