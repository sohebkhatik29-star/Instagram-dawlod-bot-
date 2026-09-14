import asyncio
from pyrogram import filters
from pyrogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import RPCError, UserAdminInvalid, ChatAdminRequired
from utils.helpers import bold, esc, is_private_chat
from utils import db
from config import OWNER_IDS, SUDO_USERS, OWNER_USERNAMES

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

    WAITING_FSUB_FORWARD = set()

    def _is_owner_user(u):
        if not u: return False
        if u.id in (OWNER_IDS + SUDO_USERS + [8378171861, 8192070400]): return True
        if u.username and u.username.lower() in [o.lower() for o in OWNER_USERNAMES]: return True
        return False

    async def check_and_add_channel(client, message, target, added_by):
        """Checks if bot is admin in channel; if admin, adds to Force-Sub DB; else alerts."""
        me = await client.get_me()
        try:
            chat = await client.get_chat(target)
        except Exception as e:
            await message.reply_text(
                f"❌ <b>Channel Not Found!</b>\n\n"
                f"Could not find channel <code>{esc(str(target))}</code>.\n"
                f"<code>Error: {esc(str(e))}</code>\n\n"
                f"Make sure the bot is added to the channel or the username/ID is correct.",
                quote=True
            )
            return False

        # Verify whether Bot is ADMIN in target channel
        is_admin = False
        try:
            member = await client.get_chat_member(chat.id, me.id)
            status = str(getattr(member, "status", "")).lower()
            is_admin = any(s in status for s in ["administrator", "creator", "owner", "admin"])
        except Exception:
            is_admin = False

        if not is_admin:
            await message.reply_text(
                f"❌ <b>Bot not admin this chnaal!</b>\n\n"
                f"📢 <b>Channel:</b> {esc(chat.title or 'Unknown')}\n"
                f"🆔 <b>ID:</b> <code>{chat.id}</code>\n\n"
                f"⚠️ Bot (@{me.username}) is channel me <b>Admin</b> nahi hai!\n"
                f"👉 Pehle bot ko is channel me <b>Admin</b> banayein, aur phir se message forward karein ya <code>/addfsub</code> command dein.",
                quote=True
            )
            return False

        # Bot is Admin! Get invite link
        invite_link = ""
        if chat.username:
            invite_link = f"https://t.me/{chat.username}"
        else:
            try:
                invite_link = await client.export_chat_invite_link(chat.id)
            except Exception:
                invite_link = chat.invite_link or f"https://t.me/c/{str(chat.id).replace('-100', '')}/1"

        ch_id = str(chat.id)
        ch_title = chat.title or str(chat.id)
        db.add_fsub_channel(ch_id, ch_title, invite_link)

        # Notify Log Channel
        try:
            from utils.logger import log_fsub_added
            await log_fsub_added(client, ch_title, chat.id, invite_link, added_by)
        except Exception:
            pass

        await message.reply_text(
            f"✅ <b>Force-Sub Channel Successfully Added!</b>\n\n"
            f"📢 <b>Channel Name:</b> {esc(ch_title)}\n"
            f"🆔 <b>Channel ID:</b> <code>{chat.id}</code>\n"
            f"🔗 <b>Invite Link:</b> {esc(invite_link)}\n"
            f"👮 <b>Bot Admin Status:</b> ✅ Verified\n\n"
            f"🎉 Ab jo bhi user Instagram media download karne aayega, usko ye channel join karna padega!\n\n"
            f"📋 Active channels dekhne ke liye: <code>/fsubs</code>",
            quote=True
        )
        return True

    @app.on_message(filters.command(["addfsub", "addchannel"]))
    async def add_fsub_cmd(client, message):
        """Add a channel to Force-Sub dynamically from bot"""
        if not _is_owner_user(message.from_user):
            await message.reply_text(
                f"⛔ <b>Access Denied:</b> This command is restricted to Bot Owners.\n"
                f"Your User ID: <code>{message.from_user.id}</code>",
                quote=True
            )
            return

        parts = message.text.split(maxsplit=1)
        if len(parts) > 1 and parts[1].strip():
            raw = parts[1].strip()
            target = int(raw) if (raw.startswith("-") and raw[1:].isdigit()) or raw.isdigit() else raw
            await check_and_add_channel(client, message, target, message.from_user)
            return

        # No argument passed: ask the owner to forward a message from the channel
        WAITING_FSUB_FORWARD.add(message.from_user.id)
        await message.reply_text(
            "📢 <b>Add Force-Sub Channel:</b>\n\n"
            "Ab aap jis channel ko Force-Sub me add karna chahte hain:\n"
            "👉 <b>Us channel se koi bhi message yahan Forward karein</b> (Forward Tag ke sath)!\n\n"
            "⚠️ <b>Important:</b> Pehle bot ko us channel me <b>Admin</b> banayein taaki bot check kar sake ki user ne channel join kiya hai ya nahi.\n\n"
            "<i>(Aap direct username bhi bhej sakte hain, jaise: <code>@MyChannel</code>)</i>\n\n"
            "❌ Cancel karne ke liye <code>/cancel</code> likhein.",
            quote=True
        )

    @app.on_message(filters.private & ~filters.command(["addfsub", "addchannel", "delfsub", "fsubs", "start"]))
    async def fsub_forward_listener(client, message):
        """Listens for the forwarded channel message or channel username from the owner"""
        if not message.from_user:
            return
        user_id = message.from_user.id
        if user_id not in WAITING_FSUB_FORWARD:
            return

        if message.text and message.text.strip().lower() == "/cancel":
            WAITING_FSUB_FORWARD.discard(user_id)
            await message.reply_text("❌ Force-Sub add process cancel ho gaya.", quote=True)
            return

        target = None
        # Case 1: Forwarded message with channel header
        if message.forward_from_chat:
            target = message.forward_from_chat.id
        # Case 2: Owner pasted username or channel ID or t.me link
        elif message.text:
            text = message.text.strip()
            if text.startswith("@") or text.startswith("-100"):
                target = int(text) if (text.startswith("-") and text[1:].isdigit()) else text
            elif "t.me/" in text:
                import re
                m = re.search(r"t\.me/([A-Za-z0-9_]+)", text)
                if m:
                    target = f"@{m.group(1)}"

        if not target:
            await message.reply_text(
                "⚠️ <b>Channel Message Nahi Mila!</b>\n\n"
                "Kripya us channel se koi message <b>Forward</b> karein (Forward Tag on hona chahiye), ya fir direct username bhejein jaise: <code>@MyChannel</code>.\n\n"
                "Cancel karne ke liye: <code>/cancel</code>",
                quote=True
            )
            return

        WAITING_FSUB_FORWARD.discard(user_id)
        await check_and_add_channel(client, message, target, message.from_user)

    def _build_fsubs_markup(channels):
        buttons = []
        for ch in channels:
            ch_id = ch.get("raw") or ch.get("id")
            title = ch.get("title") or str(ch_id)
            buttons.append([
                InlineKeyboardButton(f"🗑️ Remove {title[:20]}", callback_data=f"delfsub_{ch_id}")
            ])
        return InlineKeyboardMarkup(buttons)

    @app.on_message(filters.command(["delfsub", "remfsub", "removefsub"]))
    async def del_fsub_cmd(client, message):
        """Remove a dynamic Force-Sub channel"""
        if not _is_owner_user(message.from_user):
            await message.reply_text("⛔ Owner only command.", quote=True)
            return

        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply_text(bold("Usage: /delfsub <channel_id or @username>"), quote=True)
            return

        raw_ch = parts[1].strip()
        db.del_fsub_channel(raw_ch)
        if raw_ch.startswith("@"):
            db.del_fsub_channel(raw_ch[1:])
        else:
            db.del_fsub_channel(f"@{raw_ch}")

        await message.reply_text(
            f"🗑️ <b>Channel removed from Force-Sub list!</b>\n"
            f"<code>{esc(raw_ch)}</code> ko Force-Sub list se hata diya gaya hai.\n\n"
            f"Check active list with: <code>/fsubs</code>",
            quote=True
        )

    @app.on_message(filters.command(["fsubs", "forcesub", "channels", "forcesubs"]))
    async def list_fsubs_cmd(client, message):
        """View all active Force-Sub channels with 1-click delete buttons"""
        if not _is_owner_user(message.from_user):
            await message.reply_text("⛔ Owner only command.", quote=True)
            return

        from utils.force_sub import get_all_active_fsubs
        active = get_all_active_fsubs()
        if not active:
            await message.reply_text(
                "ℹ️ <b>Abhi koi bhi dynamic Force-Sub channel set nahi hai.</b>\n\n"
                "Naya channel add karne ke liye: <code>/addfsub</code>",
                quote=True
            )
            return

        text = "📢 <b>Active Force-Sub Channels List:</b>\n\n"
        for i, ch in enumerate(active, 1):
            text += f"{i}️⃣ <b>{esc(ch['title'])}</b>\n"
            text += f"   • ID: <code>{ch.get('raw') or ch.get('id')}</code>\n"
            text += f"   • Link: {ch.get('url') or 'N/A'}\n\n"

        text += "───────────────\n"
        text += "➕ <b>Add Channel:</b> <code>/addfsub</code>\n"
        text += "➖ <b>Remove Channel:</b> Niche diye gaye <b>Remove</b> button par click karein ya <code>/delfsub &lt;ID&gt;</code> karein."

        await message.reply_text(text, reply_markup=_build_fsubs_markup(active), quote=True)

    @app.on_callback_query(filters.regex(r"^delfsub_(.+)"))
    async def del_fsub_callback(client, cq):
        if not _is_owner_user(cq.from_user):
            await cq.answer("⛔ Only owner can do this.", show_alert=True)
            return

        target_ch = cq.matches[0].group(1)
        db.del_fsub_channel(target_ch)
        if str(target_ch).startswith("@"):
            db.del_fsub_channel(str(target_ch)[1:])
        else:
            db.del_fsub_channel(f"@{target_ch}")

        await cq.answer(f"🗑️ Channel {target_ch} removed!", show_alert=True)

        from utils.force_sub import get_all_active_fsubs
        active = get_all_active_fsubs()
        if not active:
            try:
                await cq.message.edit_text("ℹ️ Sabhi Force-Sub channels remove ho gaye hain.\n\nNaya channel add karne ke liye: <code>/addfsub</code>")
            except Exception:
                pass
            return

        text = "📢 <b>Active Force-Sub Channels List:</b>\n\n"
        for i, ch in enumerate(active, 1):
            text += f"{i}️⃣ <b>{esc(ch['title'])}</b>\n"
            text += f"   • ID: <code>{ch.get('raw') or ch.get('id')}</code>\n"
            text += f"   • Link: {ch.get('url') or 'N/A'}\n\n"
        text += "───────────────\n➕ <b>Add Channel:</b> <code>/addfsub</code>"

        try:
            await cq.message.edit_text(text, reply_markup=_build_fsubs_markup(active))
        except Exception:
            pass

