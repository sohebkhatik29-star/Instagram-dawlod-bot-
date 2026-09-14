import threading
import logging
import asyncio
from utils.autoinstall import ensure_dependencies

# Auto check & install dependencies
ensure_dependencies()

from pyrogram import Client, idle
from config import API_ID, API_HASH, BOT_TOKEN, PORT, BOT_NAME, OWNER_LINK, UPDATE_CHANNEL_URL
from web_server import run_web_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("MOVIES_1780_BOT")

def start_web():
    try:
        run_web_server(PORT)
    except Exception as e:
        log.warning(f"Web server error: {e}")

async def run_bot():
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN is required! Please configure it in your .env file or host environment.")
        return

    app = Client(
        name="movies_insta_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
    )

    from plugins import start, downloader, admin, broadcast, misc
    start.register(app)
    downloader.register(app)
    admin.register(app)
    broadcast.register(app)
    misc.register(app)

    await app.start()
    me = await app.get_me()

    # Register native Telegram [Menu] commands button
    try:
        from pyrogram.types import BotCommand
        await app.set_bot_commands([
            BotCommand("start", "Start bot & open main dashboard"),
            BotCommand("help", "Help & list of commands"),
            BotCommand("about", "About bot & owner details"),
            BotCommand("dl", "Download Instagram Reel/Post/Video"),
            BotCommand("addfsub", "➕ Add Force-Sub Channel (Owner)"),
            BotCommand("delfsub", "➖ Remove Force-Sub Channel (Owner)"),
            BotCommand("fsubs", "📢 View All Force-Sub Channels"),
            BotCommand("ping", "Check bot latency & speed"),
            BotCommand("id", "Get Telegram chat and user ID"),
            BotCommand("info", "View user details"),
            BotCommand("stats", "View bot stats (Owner only)")
        ])
        log.info("✅ Telegram native Menu commands registered!")
    except Exception as e:
        log.warning(f"Could not register bot commands menu: {e}")

    log.info(f"✅ Bot successfully running as @{me.username}!")
    log.info(f"👑 Owner: @movies_1780 ({OWNER_LINK})")
    log.info(f"📢 Updates Channel: {UPDATE_CHANNEL_URL}")
    await idle()
    await app.stop()

def main():
    log.info(f"🚀 Booting {BOT_NAME}...")
    threading.Thread(target=start_web, daemon=True).start()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_bot())
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down bot safely...")
    finally:
        loop.close()

if __name__ == "__main__":
    main()
