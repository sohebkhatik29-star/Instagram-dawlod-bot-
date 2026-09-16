import os
import time
import asyncio
import logging
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.helpers import bold, esc, is_private_chat, is_owner_user, ensure_owner_commands
from utils.force_sub import is_subscribed, join_markup, join_text, get_unsubscribed_channels
from utils import db
from utils.logger import log_new_user
from config import BOT_NAME, FORCE_SUB_CHANNEL, UPDATE_CHANNEL_URL, SUPPORT_GROUP_URL, START_PHOTO_URL, START_PIC_PATH

START_TIME = time.time()
log = logging.getLogger("START_PLUGIN")

def start_menu(is_owner=False):
    buttons = []
    if is_owner:
        buttons.append([
            InlineKeyboardButton("👑 Owner Dashboard / Admin Panel", callback_data="open_owner_panel")
        ])
    buttons.extend([
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
    return InlineKeyboardMarkup(buttons)

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
        f"👋 <b>Hey {user_mention}!</b>\n\n"
        f"⚡ <b>Ash Insta Downloader</b>\n"
        f"Send any Instagram link (Reel, Video, Post) to download instantly in HD quality!"
    )

def get_about_text():
    uptime_sec = int(time.time() - START_TIME)
    hours, rem = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(rem, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    return (
        f"ℹ️ <b>About Bot:</b>\n\n"
        f"🤖 <b>Name:</b> Ash Insta Downloader\n"
        f"⚡ <b>Speed:</b> Super Fast\n"
        f"🎬 <b>Quality:</b> 1080p Full HD\n"
        f"⏱️ <b>Uptime:</b> {uptime_str}\n"
        f"🟢 <b>Status:</b> 24/7 Active"
    )

async def _edit_or_reply(cq, text, reply_markup=None):
    """Safely edits caption on photo messages, edits text on text messages, or sends reply"""
    if cq.message:
        try:
            if cq.message.photo:
                await cq.message.edit_caption(caption=text, reply_markup=reply_markup)
                return
            else:
                await cq.message.edit_text(text=text, reply_markup=reply_markup)
                return
        except Exception:
            pass
    try:
        await cq.message.reply_text(text, reply_markup=reply_markup, quote=True)
    except Exception:
        pass

def register(app):
    @app.on_message((filters.command(["start", "startbot"]) | filters.regex(r"^/start")), group=0)
    async def start_cmd(client, message):
        try:
            user = message.from_user
            if not user:
                return

            log.info(f"[/start] Received from user {user.id} (@{user.username or 'none'})")

            try:
                is_new = db.add_user(user.id, user.username or "", user.first_name or "")
                if is_new:
                    tot_u, _ = db.stats()
                    asyncio.create_task(log_new_user(client, user, tot_u))
            except Exception as e:
                log.warning(f"DB error in start: {e}")

            is_owner = is_owner_user(user)

            # If in a group chat
            if not is_private_chat(message):
                try:
                    db.add_chat(message.chat.id, message.chat.title or "")
                except Exception:
                    pass
                await message.reply_text(
                    bold(f"👋 Hey {esc(user.first_name)}! I'm {BOT_NAME}.\n\nSend any Instagram link here and I will download it for you!\nUse the buttons below to check commands or join our discussion group."),
                    reply_markup=start_menu(is_owner),
                    quote=True
                )
                return

            # Non-blocking registration of owner commands menu
            if is_owner:
                asyncio.create_task(ensure_owner_commands(client, message.chat.id))

            caption = get_welcome_text(user)

            photo_to_send = None
            if os.path.exists(START_PIC_PATH):
                photo_to_send = START_PIC_PATH
            elif START_PHOTO_URL:
                photo_to_send = START_PHOTO_URL

            sent = False
            if photo_to_send:
                try:
                    await asyncio.wait_for(
                        message.reply_photo(photo=photo_to_send, caption=caption, reply_markup=start_menu(is_owner), quote=True),
                        timeout=5.0
                    )
                    sent = True
                except Exception as e:
                    log.warning(f"Could not send start photo banner: {e}")

            if not sent:
                await message.reply_text(caption, reply_markup=start_menu(is_owner), quote=True)
        except Exception as e:
            log.error(f"Fatal error in start_cmd: {e}", exc_info=True)
            try:
                await message.reply_text(
                    f"👋 Welcome to <b>{BOT_NAME}</b>!\n\nSend me any Instagram link to download.",
                    reply_markup=start_menu(is_owner_user(message.from_user)),
                    quote=True
                )
            except Exception:
                pass

    @app.on_callback_query(filters.regex("^check_sub$"))
    async def check_sub_cb(client, cq):
        unjoined = await get_unsubscribed_channels(client, cq.from_user.id)
        if not unjoined:
            await cq.answer("✅ Channel Joined Successfully!", show_alert=True)
            try:
                await cq.message.edit_text(
                    "✅ <b>Channels Verified Successfully!</b>\n\n"
                    "Ab aap koi bhi Instagram video / reel ka link bhej sakte hain, bot turant download kar dega! 🚀",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main")
                    ]])
                )
            except Exception:
                await _edit_or_reply(cq, get_welcome_text(cq.from_user), reply_markup=start_menu())
        else:
            await cq.answer("❌ You haven't joined all required channels yet! Please join first.", show_alert=True)
            await _edit_or_reply(cq, join_text(unjoined), reply_markup=join_markup(unjoined))

    @app.on_callback_query(filters.regex("^show_about$"))
    async def about_cb(client, cq):
        await cq.answer()
        await _edit_or_reply(cq, get_about_text(), reply_markup=back_menu())

    @app.on_callback_query(filters.regex("^show_help$"))
    async def help_cb(client, cq):
        await cq.answer()
        from plugins.misc import HELP_TEXT
        await _edit_or_reply(cq, HELP_TEXT, reply_markup=back_menu())

    @app.on_callback_query(filters.regex("^show_ping$"))
    async def ping_cb(client, cq):
        start = time.time()
        await cq.answer("Checking ping...")
        ms = (time.time() - start) * 1000
        text = (
            f"🏓 <b>Pong:</b> <code>{ms:.2f} ms</code>\n\n"
            f"⚡ <b>Speed:</b> 100% Fast\n"
            f"🟢 <b>Status:</b> Online"
        )
        await _edit_or_reply(cq, text, reply_markup=back_menu())

    @app.on_callback_query(filters.regex("^back_to_main$"))
    async def back_to_main_cb(client, cq):
        await cq.answer()
        is_owner = is_owner_user(cq.from_user)
        if is_owner and cq.message and cq.message.chat:
            await ensure_owner_commands(client, cq.message.chat.id)
        await _edit_or_reply(cq, get_welcome_text(cq.from_user), reply_markup=start_menu(is_owner))
