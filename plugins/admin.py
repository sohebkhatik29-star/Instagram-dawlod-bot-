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
