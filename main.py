import threading
import logging
import asyncio
from utils.autoinstall import ensure_dependencies

# Auto check & install dependencies
ensure_dependencies()

from pyrogram import Client, idle
from config import API_ID, API_HASH, BOT_TOKEN, PORT, BOT_NAME, UPDATE_CHANNEL_URL, SUPPORT_GROUP_URL
from web_server import run_web_server
from utils.logger import log_bot_restart

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

    # Register native Telegram [Menu] commands button (Public vs Owner scopes)
    try:
        from pyrogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
        from config import OWNER_IDS, SUDO_USERS

        public_commands = [
            BotCommand("start", "Start bot & open main dashboard")
        ]
        await app.set_bot_commands(public_commands, scope=BotCommandScopeDefault())
        log.info("✅ Public Telegram Menu registered with only /start for standard users!")

        owner_commands = [
            BotCommand("start", "Start bot & open main dashboard"),
            BotCommand("admin", "👑 Owner / Admin Control Panel"),
            BotCommand("broadcast", "📢 Broadcast message"),
            BotCommand("broadcast_pin", "📌 Broadcast & Pin message"),
            BotCommand("unpin", "📍 Unpin broadcast message"),
            BotCommand("unpinall", "🗑️ Unpin all messages"),
            BotCommand("admins", "🛡️ Manage Admins"),
            BotCommand("addfsub", "➕ Add Force-Sub Channel"),
            BotCommand("delfsub", "➖ Remove Force-Sub Channel"),
            BotCommand("fsubs", "📢 View All Force-Sub Channels"),
            BotCommand("stats", "📊 View bot stats & users"),
            BotCommand("help", "Help & guide"),
            BotCommand("ping", "Check bot latency & speed")
        ]
        for oid in set(OWNER_IDS + SUDO_USERS + [5566977478]):
            try:
                await app.set_bot_commands(owner_commands, scope=BotCommandScopeChat(chat_id=oid))
            except Exception:
                pass
        log.info("✅ Owner Telegram Menu commands registered for authorized owners!")
    except Exception as e:
        log.warning(f"Could not register bot commands menu: {e}")

    log.info(f"✅ Bot successfully running as @{me.username}!")
    log.info(f"📢 Updates Channel: {UPDATE_CHANNEL_URL}")
    log.info(f"💬 Discussion Group: {SUPPORT_GROUP_URL}")

    # Notify log channel that bot restarted
    try:
        await log_bot_restart(app, me)
    except Exception as e:
        log.warning(f"Could not send restart log: {e}")

    # Keep bot running continuously 24/7 without premature termination
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
        log.info("Stopping bot gracefully...")
    finally:
        try:
            await app.stop()
        except Exception:
            pass

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
