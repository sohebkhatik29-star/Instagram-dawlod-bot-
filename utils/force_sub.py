import logging
from pyrogram.errors import UserNotParticipant, RPCError, ChatAdminRequired
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import FORCE_SUB_CHANNEL, UPDATE_CHANNEL_URL, SUPPORT_GROUP_URL
from utils.helpers import bold
from utils import db

log = logging.getLogger("FORCE_SUB")

def _normalize_target(ch_identifier):
    ch = str(ch_identifier or "").strip()
    if ch.startswith("https://t.me/"):
        ch = ch.replace("https://t.me/", "")
    if ch.startswith("@"):
        ch = ch[1:]
    if not ch:
        return None
    if ch.startswith("-100") or (ch.startswith("-") and ch[1:].isdigit()):
        return int(ch)
    elif ch.isdigit():
        return int(f"-100{ch}")
    else:
        return f"@{ch}"

def get_all_active_fsubs():
    """Returns list of dict: [{'id': target_id, 'title': title, 'url': link}]"""
    channels = []
    disabled = set(db.get_disabled_fsubs())
    
    # 1. Default channel from config/env
    default_ch = str(FORCE_SUB_CHANNEL or "").strip()
    if default_ch and default_ch not in disabled and f"@{default_ch.replace('@','')}" not in disabled and default_ch.replace("@", "") not in disabled:
        ch_clean = default_ch.replace("https://t.me/", "").replace("@", "")
        channels.append({
            "id": _normalize_target(default_ch),
            "raw": default_ch,
            "title": f"@{ch_clean}",
            "url": UPDATE_CHANNEL_URL or f"https://t.me/{ch_clean}"
        })

    # 2. Dynamic channels from database
    db_channels = db.get_all_fsub_channels()
    for ch_id, title, invite_link in db_channels:
        if ch_id in disabled or f"@{ch_id.replace('@','')}" in disabled or ch_id.replace("@", "") in disabled:
            continue
        norm = _normalize_target(ch_id)
        # Avoid duplicate if same as default
        if any(c["raw"] == ch_id or str(c["id"]) == str(norm) for c in channels):
            continue
        link = invite_link.strip() if invite_link else (f"https://t.me/{ch_id.replace('@','')}" if not str(ch_id).startswith("-") else None)
        channels.append({
            "id": norm,
            "raw": ch_id,
            "title": title or str(ch_id),
            "url": link or f"https://t.me/{str(ch_id).replace('@','')}"
        })

    return channels

async def check_user_channel(client, user_id, target):
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
        log.warning(f"⚠️ Bot is not an Admin in channel {target}! Please promote bot as Admin for force-sub to work.")
        return True
    except RPCError as e:
        if "USER_NOT_PARTICIPANT" in str(e).upper():
            return False
        log.warning(f"Force-sub RPCError: {e}")
        return True
    except Exception as e:
        if "USER_NOT_PARTICIPANT" in str(e).upper():
            return False
        log.warning(f"Error checking subscription for user {user_id} in {target}: {e}")
        return True

async def get_unsubscribed_channels(client, user_id):
    """Returns list of channels user hasn't joined yet"""
    fsubs = get_all_active_fsubs()
    unjoined = []
    for ch in fsubs:
        target = ch.get("id")
        if not target:
            continue
        subbed = await check_user_channel(client, user_id, target)
        if not subbed:
            unjoined.append(ch)
    return unjoined

async def is_subscribed(client, user_id):
    unjoined = await get_unsubscribed_channels(client, user_id)
    return len(unjoined) == 0

def join_markup(unjoined_channels=None):
    if unjoined_channels is None:
        unjoined_channels = get_all_active_fsubs()

    buttons = []
    # Add a join button for each required channel numbered "Join Channel 1", "Join Channel 2", etc.
    for idx, ch in enumerate(unjoined_channels, 1):
        btn_label = f"📢 Join Channel {idx}"
        buttons.append([InlineKeyboardButton(btn_label, url=ch["url"])])

    # Check button
    buttons.append([InlineKeyboardButton("✅ I've Joined — Unlock Bot", callback_data="check_sub")])

    return InlineKeyboardMarkup(buttons)

def join_text(unjoined_channels=None):
    if unjoined_channels is None:
        unjoined_channels = get_all_active_fsubs()

    ch_list_str = ""
    for idx, ch in enumerate(unjoined_channels, 1):
        ch_list_str += f"👉 <b>Join Channel {idx}</b>\n"

    return (
        "🔒 <b>Channel Join Required!</b>\n\n"
        "Aapne abhi tak hamare required channel(s) join nahi kiye hain.\n\n"
        "Video / Reel download karne ke liye pehle niche diye gaye channel(s) ko join karein:\n\n"
        f"{ch_list_str}\n"
        "1. Upar diye gaye <b>Join Channel</b> button par click karke <b>Join</b> karein.\n"
        "2. Uske baad <b>'✅ I've Joined — Unlock Bot'</b> dabayein aur turant download start karein!"
    )
