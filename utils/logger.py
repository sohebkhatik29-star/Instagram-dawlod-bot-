import datetime, logging
from config import LOG_CHANNEL_ID, BOT_NAME, FORCE_SUB_CHANNEL, SUPPORT_GROUP_URL
from utils.helpers import esc

log = logging.getLogger("LOG_CHANNEL")

async def send_log(client, text):
    if not LOG_CHANNEL_ID:
        return
    try:
        await client.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=text,
            disable_web_page_preview=True
        )
    except Exception as e:
        log.warning(f"Failed to send message to Log Channel ({LOG_CHANNEL_ID}): {e}")

async def log_bot_restart(client, bot_me):
    now_utc = datetime.datetime.utcnow().strftime("%d-%b-%Y %I:%M:%S %p UTC")
    text = (
        f"⚡ <b>{BOT_NAME} Started Successfully!</b>\n\n"
        f"🤖 <b>Bot:</b> @{bot_me.username}\n"
        f"🆔 <b>Bot ID:</b> <code>{bot_me.id}</code>\n"
        f"🕒 <b>Restart Time:</b> <code>{now_utc}</code>\n"
        f"🚀 <b>Status:</b> Online 24/7 & Ready to Download!\n\n"
        f"📢 <b>Updates:</b> @{FORCE_SUB_CHANNEL}\n"
        f"💬 <b>Group:</b> @ash_movie_j"
    )
    await send_log(client, text)

async def log_new_user(client, user, total_users):
    if not user:
        return
    username_str = f"@{user.username}" if user.username else "No Username"
    text = (
        f"👤 <b>#NEW_USER Started Bot!</b>\n\n"
        f"• <b>Name:</b> {esc(user.first_name)} {esc(user.last_name or '')}\n"
        f"• <b>User ID:</b> <code>{user.id}</code>\n"
        f"• <b>Username:</b> {username_str}\n"
        f"• <b>Total Users:</b> <code>{total_users}</code>"
    )
    await send_log(client, text)

async def log_download(client, user, format_title, url):
    user_str = esc(user.first_name) if user else "Unknown"
    uid = user.id if user else 0
    username_str = f"@{user.username}" if user and user.username else "No Username"
    text = (
        f"📥 <b>#DOWNLOAD_COMPLETED</b>\n\n"
        f"• <b>User:</b> {user_str} (<code>{uid}</code>)\n"
        f"• <b>Username:</b> {username_str}\n"
        f"• <b>Format:</b> {esc(format_title)}\n"
        f"• <b>Link:</b> {esc(url)}\n"
        f"• <b>Status:</b> ✅ Delivered to user"
    )
    await send_log(client, text)

async def log_fsub_added(client, chat_title, chat_id, invite_link, added_by):
    by_name = esc(added_by.first_name) if added_by else "Owner"
    by_id = added_by.id if added_by else 0
    text = (
        f"📢 <b>#NEW_FORCE_SUB Channel Added!</b>\n\n"
        f"• <b>Channel Name:</b> {esc(chat_title)}\n"
        f"• <b>Channel ID:</b> <code>{chat_id}</code>\n"
        f"• <b>Link:</b> {esc(invite_link or 'N/A')}\n"
        f"• <b>Added By:</b> {by_name} (<code>{by_id}</code>)"
    )
    await send_log(client, text)
