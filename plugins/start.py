import time
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.helpers import bold, esc, is_private_chat
from utils.force_sub import is_subscribed, join_markup, join_text, get_unsubscribed_channels
from utils import db
from utils.logger import log_new_user
from config import BOT_NAME, FORCE_SUB_CHANNEL, UPDATE_CHANNEL_URL, SUPPORT_GROUP_URL

START_TIME = time.time()

def start_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Updates Channel", url=UPDATE_CHANNEL_URL),
            InlineKeyboardButton("💬 Discussion Group", url=SUPPORT_GROUP_URL),
        ],
        [
            InlineKeyboardButton("📖 Help & Commands", callback_data="show_help"),
            InlineKeyboardButton("ℹ️ About Bot", callback_data="show_about"),
        ],
        [
            InlineKeyboardButton("🏓 Ping & Status", callback_data="show_ping"),
        ]
    ])

def back_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main"),
            InlineKeyboardButton("📢 Updates Channel", url=UPDATE_CHANNEL_URL),
        ],
        [
            InlineKeyboardButton("💬 Discussion Group", url=SUPPORT_GROUP_URL),
        ]
    ])

def get_welcome_text(user):
    if user:
        mention = getattr(user, "mention", None)
        if callable(mention):
            user_mention = user.mention(style="html")
        elif isinstance(mention, str):
            user_mention = mention
        else:
            user_mention = f'<a href="tg://user?id={user.id}">{esc(user.first_name or "Friend")}</a>'
    else:
        user_mention = "Friend"

    return (
        f"👋 Hello {user_mention}, welcome to <b>Ash Insta Downloader Bot</b>! ⚡\n\n"
        f"I'm an advanced Instagram Downloader Bot.\n"
        f"Send any Instagram Reel, Video, or Post link here and I will download it for you instantly in high quality!\n\n"
        f"ℹ️ <b>More info to click Help button below!</b>\n\n"
        f"───────────────\n"
        f"📢 <b>Updates Channel:</b> @{FORCE_SUB_CHANNEL}\n"
        f"💬 <b>Discussion Group:</b> @ash_movie_j"
    )

def get_about_text():
    uptime_sec = int(time.time() - START_TIME)
    hours, rem = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(rem, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    return (
        f"ℹ️ <b>About Ash Insta Downloader Bot</b>\n\n"
        f"• <b>Bot Name:</b> Ash Insta Downloader Bot\n"
        f"• <b>Updates Channel:</b> @{FORCE_SUB_CHANNEL}\n"
        f"• <b>Discussion Group:</b> @ash_movie_j\n"
        f"• <b>Engine:</b> Python 3 + Pyrogram 2.0 + High-Speed yt-dlp\n"
        f"• <b>Quality:</b> Original Full HD (1080p)\n"
        f"• <b>Uptime:</b> {uptime_str}\n"
        f"• <b>Status:</b> 24/7 Always Online\n\n"
        f"💡 Need help or join community? Visit our Discussion Group: https://t.me/ash_movie_j"
    )

def register(app):
    @app.on_message(filters.command("start"))
    async def start_cmd(client, message):
        user = message.from_user
        if not user:
            return

        is_new = db.add_user(user.id, user.username or "", user.first_name or "")
        if is_new:
            try:
                tot_u, _ = db.stats()
                await log_new_user(client, user, tot_u)
            except Exception:
                pass

        # If in a group chat
        if not is_private_chat(message):
            db.add_chat(message.chat.id, message.chat.title or "")
            await message.reply_text(
                bold(f"👋 Hey {esc(user.first_name)}! I'm {BOT_NAME}.\n\nSend any Instagram link here and I will download it for you!\nUse the buttons below to check commands or join our discussion group."),
                reply_markup=start_menu(),
                quote=True
            )
            return

        # Private Chat: Check Force-Subscribe to all required channels
        unjoined = await get_unsubscribed_channels(client, user.id)
        if unjoined:
            await message.reply_text(join_text(unjoined), reply_markup=join_markup(unjoined), quote=True)
            return

        caption = get_welcome_text(user)

        try:
            photos = [p async for p in client.get_chat_photos(user.id, limit=1)]
            photo = photos[0] if photos else None
        except Exception:
            photo = None

        if photo:
            await message.reply_photo(photo.file_id, caption=caption, reply_markup=start_menu(), quote=True)
        else:
            await message.reply_text(caption, reply_markup=start_menu(), quote=True)

    @app.on_callback_query(filters.regex("^check_sub$"))
    async def check_sub_cb(client, cq):
        unjoined = await get_unsubscribed_channels(client, cq.from_user.id)
        if not unjoined:
            await cq.answer("✅ Verified! Welcome to the bot.", show_alert=True)
            try:
                await cq.message.edit_text(get_welcome_text(cq.from_user), reply_markup=start_menu())
            except Exception:
                await cq.message.delete()
                await client.send_message(cq.from_user.id, get_welcome_text(cq.from_user), reply_markup=start_menu())
        else:
            await cq.answer("❌ You haven't joined all required channels yet! Please join first.", show_alert=True)
            try:
                await cq.message.edit_text(join_text(unjoined), reply_markup=join_markup(unjoined))
            except Exception:
                pass

    @app.on_callback_query(filters.regex("^show_about$"))
    async def about_cb(client, cq):
        await cq.answer()
        try:
            await cq.message.edit_text(get_about_text(), reply_markup=back_menu())
        except Exception:
            await cq.message.reply_text(get_about_text(), reply_markup=back_menu(), quote=True)

    @app.on_callback_query(filters.regex("^show_help$"))
    async def help_cb(client, cq):
        await cq.answer()
        from plugins.misc import HELP_TEXT
        try:
            await cq.message.edit_text(HELP_TEXT, reply_markup=back_menu())
        except Exception:
            await cq.message.reply_text(HELP_TEXT, reply_markup=back_menu(), quote=True)

    @app.on_callback_query(filters.regex("^show_ping$"))
    async def ping_cb(client, cq):
        start = time.time()
        await cq.answer("Checking ping...")
        ms = (time.time() - start) * 1000
        text = bold(f"🏓 <b>Pong Latency:</b> <code>{ms:.2f} ms</code>\n🚀 <b>Server Status:</b> Running at 100% speed\n📢 <b>Updates Channel:</b> @{FORCE_SUB_CHANNEL}\n💬 <b>Discussion Group:</b> @ash_movie_j")
        try:
            await cq.message.edit_text(text, reply_markup=back_menu())
        except Exception:
            await cq.message.reply_text(text, reply_markup=back_menu(), quote=True)

    @app.on_callback_query(filters.regex("^back_to_main$"))
    async def back_to_main_cb(client, cq):
        await cq.answer()
        try:
            await cq.message.edit_text(get_welcome_text(cq.from_user), reply_markup=start_menu())
        except Exception:
            await cq.message.reply_text(get_welcome_text(cq.from_user), reply_markup=start_menu(), quote=True)
