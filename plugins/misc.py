import time
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.helpers import bold, esc
from utils import db
from config import OWNER_IDS, SUDO_USERS, BOT_NAME, SUPPORT_GROUP_URL, FORCE_SUB_CHANNEL, UPDATE_CHANNEL_URL

HELP_TEXT = (
    "📖 <b>How to Download:</b>\n\n"
    "1️⃣ <b>Send Link</b> — Paste any Instagram Reel or Post link.\n"
    "2️⃣ <b>Select Format</b> — Choose Video, MP4, or MP3 Audio.\n"
    "3️⃣ <b>Done</b> — Bot delivers media in 2 seconds!"
)

def register(app):
    @app.on_message(filters.command("help"))
    async def help_cmd(client, message):
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 Updates Channel", url=UPDATE_CHANNEL_URL),
                InlineKeyboardButton("💬 Discussion Group", url=SUPPORT_GROUP_URL),
            ]
        ])
        await message.reply_text(HELP_TEXT, reply_markup=kb, quote=True)

    @app.on_message(filters.command("about"))
    async def about_cmd(client, message):
        from plugins.start import get_about_text, start_menu
        await message.reply_text(get_about_text(), reply_markup=start_menu(), quote=True)

    @app.on_message(filters.command("ping"))
    async def ping_cmd(client, message):
        start = time.time()
        sent = await message.reply_text(bold("🏓 Pinging servers..."), quote=True)
        ms = (time.time() - start) * 1000
        await sent.edit_text(bold(f"🏓 Pong! Latency: {ms:.2f} ms\nBot is running smoothly!"))

    @app.on_message(filters.command("id"))
    async def id_cmd(client, message):
        target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
        text = bold(
            f"🆔 <b>Telegram IDs:</b>\n"
            f"• Chat ID: <code>{message.chat.id}</code>\n"
            f"• User ID: <code>{target.id if target else 'N/A'}</code>"
        )
        await message.reply_text(text, quote=True)

    @app.on_message(filters.command("info"))
    async def info_cmd(client, message):
        target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
        if not target:
            await message.reply_text(bold("Could not resolve user details."), quote=True)
            return

        text = bold(
            f"👤 <b>User Info:</b>\n\n"
            f"• ID: <code>{target.id}</code>\n"
            f"• First Name: {esc(target.first_name)}\n"
            f"• Last Name: {esc(target.last_name or 'None')}\n"
            f"• Username: @{target.username if target.username else 'None'}\n"
            f"• Is Bot: {'Yes' if target.is_bot else 'No'}\n"
            f"• Premium: {'Yes' if getattr(target, 'is_premium', False) else 'No'}"
        )
        await message.reply_text(text, quote=True)

    @app.on_message(filters.command("stats"))
    async def stats_cmd(client, message):
        from config import OWNER_USERNAMES, FORCE_SUB_CHANNEL
        from plugins.start import START_TIME
        is_owner = (
            message.from_user.id in (OWNER_IDS + SUDO_USERS) or
            (message.from_user.username and any(message.from_user.username.lower() == o.lower() for o in OWNER_USERNAMES if o))
        )
        if not is_owner:
            await message.reply_text(bold("⛔ This command is restricted to bot owners."), quote=True)
            return

        u, c = db.stats()
        dl_count = db.total_downloads()
        fsubs = db.get_all_fsub_channels()

        uptime_sec = int(time.time() - START_TIME)
        hours, rem = divmod(uptime_sec, 3600)
        minutes, seconds = divmod(rem, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        await message.reply_text(
            bold(
                f"📊 <b>Ash Insta Downloader — Statistics & Analytics</b>\n\n"
                f"👤 <b>Total Users (Bot Used):</b> <code>{u}</code>\n"
                f"👥 <b>Total Active Groups:</b> <code>{c}</code>\n"
                f"📥 <b>Total Downloads Served:</b> <code>{dl_count}</code>\n"
                f"📢 <b>Active Force-Sub Channels:</b> <code>{len(fsubs)}</code>\n"
                f"⏱️ <b>Server Uptime:</b> <code>{uptime_str}</code>\n"
                f"⚡ <b>Engine Status:</b> 24/7 Running Smoothly"
            ),
            quote=True
        )
