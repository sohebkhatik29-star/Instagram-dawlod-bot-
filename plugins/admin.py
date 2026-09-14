import asyncio
from pyrogram import filters
from pyrogram.types import ChatPermissions
from pyrogram.errors import RPCError, UserAdminInvalid, ChatAdminRequired
from utils.helpers import bold, esc, is_private_chat
from utils import db
from config import OWNER_IDS, SUDO_USERS

async def is_admin(client, chat_id, user_id):
    if user_id in (OWNER_IDS + SUDO_USERS): return True
    try:
        m = await client.get_chat_member(chat_id, user_id)
        status = str(getattr(m, "status", "")).lower()
        return any(s in status for s in ["administrator", "creator", "owner", "admin"])
    except: return False

async def bot_is_admin(client, chat_id):
    try:
        me = await client.get_me()
        m = await client.get_chat_member(chat_id, me.id)
        return m.status in ("administrator","creator","owner")
    except: return False

async def resolve(client, message):
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
    parts = message.command[1:]
    if not parts: return None
    try: return await client.get_users(parts[0])
    except: return None

async def guard(client, message):
    if is_private_chat(message):
        await message.reply_text(bold("This command only works in groups."), quote=True)
        return False
    if not await is_admin(client, message.chat.id, message.from_user.id):
        await message.reply_text(bold("You must be a group admin to use this."), quote=True)
        return False
    if not await bot_is_admin(client, message.chat.id):
        await message.reply_text(bold("Please make me an admin first!"), quote=True)
        return False
    return True

def register(app):

    @app.on_message(filters.command("mute") & filters.group)
    async def mute_cmd(client, message):
        if not await guard(client, message): return
        target = await resolve(client, message)
        if not target:
            await message.reply_text(bold("Reply to a user or give username to mute."), quote=True); return
        try:
            await client.restrict_chat_member(message.chat.id, target.id, ChatPermissions())
            await message.reply_text(bold(f"Muted {esc(target.first_name)}."), quote=True)
        except (UserAdminInvalid, ChatAdminRequired):
            await message.reply_text(bold("Can't mute this user (they may be an admin)."), quote=True)
        except RPCError as e:
            await message.reply_text(bold(f"Failed: {esc(e)}"), quote=True)

    @app.on_message(filters.command("unmute") & filters.group)
    async def unmute_cmd(client, message):
        if not await guard(client, message): return
        target = await resolve(client, message)
        if not target:
            await message.reply_text(bold("Reply to a user or give username to unmute."), quote=True); return
        try:
            await client.restrict_chat_member(message.chat.id, target.id,
                ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                                can_send_other_messages=True, can_add_web_page_previews=True))
            await message.reply_text(bold(f"Unmuted {esc(target.first_name)}."), quote=True)
        except RPCError as e:
            await message.reply_text(bold(f"Failed: {esc(e)}"), quote=True)

    @app.on_message(filters.command("ban") & filters.group)
    async def ban_cmd(client, message):
        if not await guard(client, message): return
        target = await resolve(client, message)
        if not target:
            await message.reply_text(bold("Reply to a user or give username to ban."), quote=True); return
        try:
            await client.ban_chat_member(message.chat.id, target.id)
            await message.reply_text(bold(f"Banned {esc(target.first_name)}."), quote=True)
        except RPCError as e:
            await message.reply_text(bold(f"Failed: {esc(e)}"), quote=True)

    @app.on_message(filters.command("unban") & filters.group)
    async def unban_cmd(client, message):
        if not await guard(client, message): return
        target = await resolve(client, message)
        if not target:
            await message.reply_text(bold("Reply to a user or give username to unban."), quote=True); return
        try:
            await client.unban_chat_member(message.chat.id, target.id)
            await message.reply_text(bold(f"Unbanned {esc(target.first_name)}."), quote=True)
        except RPCError as e:
            await message.reply_text(bold(f"Failed: {esc(e)}"), quote=True)

    @app.on_message(filters.command("kick") & filters.group)
    async def kick_cmd(client, message):
        if not await guard(client, message): return
        target = await resolve(client, message)
        if not target:
            await message.reply_text(bold("Reply to a user or give username to kick."), quote=True); return
        try:
            await client.ban_chat_member(message.chat.id, target.id)
            await client.unban_chat_member(message.chat.id, target.id)
            await message.reply_text(bold(f"Kicked {esc(target.first_name)}."), quote=True)
        except RPCError as e:
            await message.reply_text(bold(f"Failed: {esc(e)}"), quote=True)

    @app.on_message(filters.command("promote") & filters.group)
    async def promote_cmd(client, message):
        if not await guard(client, message): return
        target = await resolve(client, message)
        if not target:
            await message.reply_text(bold("Reply to a user or give username to promote."), quote=True); return
        try:
            from pyrogram.types import ChatPrivileges
            await client.promote_chat_member(message.chat.id, target.id,
                privileges=ChatPrivileges(can_change_info=True, can_delete_messages=True,
                    can_restrict_members=True, can_invite_users=True, can_pin_messages=True, can_manage_chat=True))
            await message.reply_text(bold(f"Promoted {esc(target.first_name)} to admin."), quote=True)
        except RPCError as e:
            await message.reply_text(bold(f"Failed: {esc(e)}"), quote=True)

    @app.on_message(filters.command("demote") & filters.group)
    async def demote_cmd(client, message):
        if not await guard(client, message): return
        target = await resolve(client, message)
        if not target:
            await message.reply_text(bold("Reply to a user or give username to demote."), quote=True); return
        try:
            from pyrogram.types import ChatPrivileges
            await client.promote_chat_member(message.chat.id, target.id, privileges=ChatPrivileges())
            await message.reply_text(bold(f"Demoted {esc(target.first_name)}."), quote=True)
        except RPCError as e:
            await message.reply_text(bold(f"Failed: {esc(e)}"), quote=True)

    @app.on_message(filters.command("pin") & filters.group)
    async def pin_cmd(client, message):
        if not await guard(client, message): return
        if not message.reply_to_message:
            await message.reply_text(bold("Reply to a message to pin it."), quote=True); return
        try:
            await message.reply_to_message.pin(disable_notification=True)
            await message.reply_text(bold("Message pinned."), quote=True)
        except RPCError as e:
            await message.reply_text(bold(f"Failed: {esc(e)}"), quote=True)

    @app.on_message(filters.command("unpin") & filters.group)
    async def unpin_cmd(client, message):
        if not await guard(client, message): return
        try:
            if message.reply_to_message:
                await message.reply_to_message.unpin()
            else:
                await client.unpin_all_chat_messages(message.chat.id)
            await message.reply_text(bold("Unpinned."), quote=True)
        except RPCError as e:
            await message.reply_text(bold(f"Failed: {esc(e)}"), quote=True)

    @app.on_message(filters.command("purge") & filters.group)
    async def purge_cmd(client, message):
        if not await guard(client, message): return
        if not message.reply_to_message:
            await message.reply_text(bold("Reply to the message to purge from."), quote=True); return
        ids = list(range(message.reply_to_message.id, message.id + 1))
        deleted = 0
        try:
            for i in range(0, len(ids), 100):
                await client.delete_messages(message.chat.id, ids[i:i+100])
                deleted += len(ids[i:i+100])
            note = await client.send_message(message.chat.id, bold(f"Purged {deleted} messages."))
            await asyncio.sleep(4)
            await note.delete()
        except RPCError as e:
            await message.reply_text(bold(f"Failed: {esc(e)}"), quote=True)

    @app.on_message(filters.command("warn") & filters.group)
    async def warn_cmd(client, message):
        if not await guard(client, message): return
        target = await resolve(client, message)
        if not target:
            await message.reply_text(bold("Reply to a user or give username to warn."), quote=True); return
        count = db.add_warn(message.chat.id, target.id)
        if count >= 3:
            try:
                await client.ban_chat_member(message.chat.id, target.id)
                db.reset_warn(message.chat.id, target.id)
                await message.reply_text(bold(f"{esc(target.first_name)} got 3 warnings and has been banned."), quote=True)
            except RPCError as e:
                await message.reply_text(bold(f"Failed to ban: {esc(e)}"), quote=True)
        else:
            await message.reply_text(bold(f"Warned {esc(target.first_name)} ({count}/3)."), quote=True)

    @app.on_message(filters.command("resetwarn") & filters.group)
    async def resetwarn_cmd(client, message):
        if not await guard(client, message): return
        target = await resolve(client, message)
        if not target:
            await message.reply_text(bold("Reply to a user or give username."), quote=True); return
        db.reset_warn(message.chat.id, target.id)
        await message.reply_text(bold(f"Warnings reset for {esc(target.first_name)}."), quote=True)

    def _is_owner_user(u):
        if not u: return False
        if u.id in (OWNER_IDS + SUDO_USERS): return True
        if u.username and u.username.lower() in [o.lower() for o in OWNER_USERNAMES]: return True
        return False

    @app.on_message(filters.command(["addfsub", "addchannel", "forcesub"]))
    async def add_fsub_cmd(client, message):
        """Add a channel to Force-Sub dynamically from bot"""
        if not _is_owner_user(message.from_user):
            await message.reply_text(bold("⛔ Owner only command."), quote=True)
            return

        # Usage: /addfsub @channelusername or /addfsub -100123456789 https://t.me/+joinlink ChannelTitle
        parts = message.text.split(maxsplit=3)
        if len(parts) < 2:
            usage = (
                "⚙️ <b>How to Add Force-Sub Channel:</b>\n\n"
                "• <b>Public Channel:</b>\n"
                "<code>/addfsub @YourChannelUsername</code>\n\n"
                "• <b>Private Channel:</b>\n"
                "<code>/addfsub -100xxxxxxxxxx https://t.me/+InviteLink Channel Title</code>\n\n"
                "💡 <i>Tip: Pehle bot ko us channel me <b>Admin</b> banao taaki bot check kar sake!</i>"
            )
            await message.reply_text(usage, quote=True)
            return

        raw_ch = parts[1].strip()
        invite_link = parts[2].strip() if len(parts) > 2 else ""
        title = parts[3].strip() if len(parts) > 3 else raw_ch

        # Test if bot can access the channel
        target = int(raw_ch) if (raw_ch.startswith("-") and raw_ch[1:].isdigit()) or raw_ch.isdigit() else raw_ch
        if not str(target).startswith("@") and not str(target).startswith("-"):
            target = f"@{target}"

        try:
            chat = await client.get_chat(target)
            ch_id = str(chat.id)
            title = chat.title or title
            if not invite_link:
                invite_link = chat.invite_link or (f"https://t.me/{chat.username}" if chat.username else "")
        except Exception as e:
            ch_id = str(raw_ch)
            if not invite_link and raw_ch.startswith("@"):
                invite_link = f"https://t.me/{raw_ch.replace('@','')}"

        db.add_fsub_channel(ch_id, title, invite_link)
        await message.reply_text(
            f"✅ <b>Force-Sub Channel Added Successfully!</b>\n\n"
            f"📢 <b>Channel:</b> {esc(title)}\n"
            f"🆔 <b>ID / User:</b> <code>{esc(ch_id)}</code>\n"
            f"🔗 <b>Link:</b> {esc(invite_link or 'N/A')}\n\n"
            f"Ab sabhi users ko ye channel join karna compulsory hoga!",
            quote=True
        )

    @app.on_message(filters.command(["delfsub", "remfsub", "removefsub"]))
    async def del_fsub_cmd(client, message):
        """Remove a dynamic Force-Sub channel"""
        if not _is_owner_user(message.from_user):
            await message.reply_text(bold("⛔ Owner only command."), quote=True)
            return

        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply_text(bold("Usage: /delfsub <channel_id or @username>"), quote=True)
            return

        raw_ch = parts[1].strip()
        db.del_fsub_channel(raw_ch)
        # also try removing without @ or with -100
        if raw_ch.startswith("@"):
            db.del_fsub_channel(raw_ch[1:])
        else:
            db.del_fsub_channel(f"@{raw_ch}")

        await message.reply_text(
            f"🗑️ <b>Channel removed from Force-Sub list!</b>\n"
            f"<code>{esc(raw_ch)}</code> ko Force-Sub list se hata diya gaya hai.",
            quote=True
        )

    @app.on_message(filters.command(["fsubs", "channels", "forcesubs"]))
    async def list_fsubs_cmd(client, message):
        """View all active Force-Sub channels"""
        if not _is_owner_user(message.from_user):
            await message.reply_text(bold("⛔ Owner only command."), quote=True)
            return

        from utils.force_sub import get_all_active_fsubs
        active = get_all_active_fsubs()
        if not active:
            await message.reply_text("ℹ️ Abhi koi bhi Force-Sub channel set nahi hai.", quote=True)
            return

        text = "📢 <b>Active Force-Sub Channels List:</b>\n\n"
        for i, ch in enumerate(active, 1):
            text += f"{i}️⃣ <b>{esc(ch['title'])}</b>\n"
            text += f"   • ID: <code>{ch.get('raw') or ch.get('id')}</code>\n"
            text += f"   • Link: {ch.get('url') or 'N/A'}\n\n"

        text += "───────────────\n"
        text += "➕ Naya add karne ke liye: <code>/addfsub @ChannelUsername</code>\n"
        text += "➖ Hatane ke liye: <code>/delfsub @ChannelUsername</code>"

        await message.reply_text(text, quote=True)

