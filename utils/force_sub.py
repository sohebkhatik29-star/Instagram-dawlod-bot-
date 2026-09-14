import logging
from pyrogram.errors import UserNotParticipant, RPCError, ChatAdminRequired
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import FORCE_SUB_CHANNEL, UPDATE_CHANNEL_URL, OWNER_LINK
from utils.helpers import bold

log = logging.getLogger("FORCE_SUB")

def clean_channel_id():
    ch = str(FORCE_SUB_CHANNEL or "MoviesGroupG3").strip()
    if ch.startswith("https://t.me/"):
        ch = ch.replace("https://t.me/", "")
    if ch.startswith("@"):
        ch = ch[1:]
    return ch

async def is_subscribed(client, user_id):
    ch = clean_channel_id()
    if not ch:
        return True

    # If it's a numeric chat ID (-100...) or username
    if ch.startswith("-100") or (ch.startswith("-") and ch[1:].isdigit()):
        target = int(ch)
    elif ch.isdigit():
        target = int(f"-100{ch}")
    else:
        target = f"@{ch}"

    try:
        member = await client.get_chat_member(target, user_id)
        status = str(getattr(member, "status", "")).lower()
        if any(s in status for s in ["member", "administrator", "creator", "owner", "admin"]):
            return True
        if any(s in status for s in ["left", "kicked", "banned"]):
            return False
        return True
    except UserNotParticipant:
        return False
    except ChatAdminRequired:
        log.warning(f"⚠️ Bot is not an Admin in channel {target}! Add the bot as Admin in your channel for Force-Sub verification to work.")
        return True
    except RPCError as e:
        if "USER_NOT_PARTICIPANT" in str(e).upper():
            return False
        log.warning(f"Force-sub RPCError: {e}")
        return True
    except Exception as e:
        if "USER_NOT_PARTICIPANT" in str(e).upper():
            return False
        log.warning(f"Error checking subscription for user {user_id}: {e}")
        return True

def join_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Join Updates Channel", url=UPDATE_CHANNEL_URL)
        ],
        [
            InlineKeyboardButton("✅ I've Joined — Unlock Bot", callback_data="check_sub")
        ],
        [
            InlineKeyboardButton("👑 Owner Support", url=OWNER_LINK)
        ]
    ])

def join_text():
    ch = clean_channel_id()
    return bold(
        f"🔒 <b>Channel Join Required!</b>\n\n"
        f"Aapne abhi tak hamara official updates channel join nahi kiya hai.\n\n"
        f"Bot use karne ke liye pehle niche diye gaye channel ko join karein:\n"
        f"📢 <b>Channel:</b> @{ch}\n\n"
        f"1. <b>'📢 Join Updates Channel'</b> par click karein aur Join karein.\n"
        f"2. Uske baad <b>'✅ I\\'ve Joined — Unlock Bot'</b> dabayein aur turant download start karein!"
    )
