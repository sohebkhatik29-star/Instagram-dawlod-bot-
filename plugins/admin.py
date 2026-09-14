import asyncio
from pyrogram import filters
from pyrogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import RPCError, UserAdminInvalid, ChatAdminRequired
from utils.helpers import bold, esc, is_private_chat, is_owner_user, ensure_owner_commands
from utils import db
from config import OWNER_IDS, SUDO_USERS, OWNER_USERNAMES

def _is_owner_user(u):
    return is_owner_user(u)

def get_owner_panel_text(user):
    u, c = db.stats()
    dl_count = db.total_downloads()
    from utils.force_sub import get_all_active_fsubs
    fsubs = get_all_active_fsubs()
    admins = db.get_all_admins()

    name = user.first_name if user and user.first_name else "Owner"
    return (
        f"👑 <b>Ash Insta Downloader — Owner Dashboard</b>\n\n"
        f"👋 Welcome back, <b>{esc(name)}</b>!\n"
        f"Yahan se aap bot ke sabhi features aur channels ko control kar sakte hain:\n\n"
        f"📊 <b>Bot Live Statistics:</b>\n"
        f"• 👤 <b>Total Users:</b> <code>{u}</code>\n"
        f"• 👥 <b>Total Groups:</b> <code>{c}</code>\n"
        f"• 📥 <b>Total Downloads:</b> <code>{dl_count}</code>\n"
        f"• 📢 <b>Force-Sub Channels:</b> <code>{len(fsubs)}</code> active\n"
        f"• 🛡️ <b>Custom Admins:</b> <code>{len(admins)}</code>\n\n"
        f"⚡ <i>Niche diye gaye buttons se koi bhi action select karein:</i>"
    )

def get_owner_panel_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="owner_action_broadcast"),
            InlineKeyboardButton("📌 Broadcast & Pin", callback_data="owner_action_bpin"),
        ],
        [
            InlineKeyboardButton("➕ Add Channel", callback_data="owner_action_addfsub"),
            InlineKeyboardButton("🗑️ Delete Channel", callback_data="owner_action_delfsub"),
        ],
        [
            InlineKeyboardButton("📢 All F-Sub Channels", callback_data="owner_action_listfsub"),
            InlineKeyboardButton("🛡️ Bot Admins", callback_data="owner_action_admins"),
        ],
        [
            InlineKeyboardButton("📊 Detailed Stats", callback_data="owner_action_stats"),
            InlineKeyboardButton("🏓 Ping Latency", callback_data="show_ping"),
        ],
        [
            InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main"),
            InlineKeyboardButton("❌ Close Panel", callback_data="close_admin_menu"),
        ]
    ])

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

    @app.on_message(filters.command(["addfsub", "addchannel", "add_fsub", "adeforcesub", "forcesub_add"]))
    async def add_fsub_cmd(client, message):
        """Add a channel to Force-Sub dynamically from bot"""
        if not _is_owner_user(message.from_user):
            await message.reply_text(
                f"⛔ <b>Access Denied:</b> This command is restricted to Bot Owners.\n"
                f"Your User ID: <code>{message.from_user.id if message.from_user else 'Unknown'}</code>\n\n"
                f"💡 Agar aap owner hain, toh apna User ID <code>{message.from_user.id if message.from_user else ''}</code> .env file me OWNER_IDS me daalein.",
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
            "<i>(Aap direct username bhi bhej sakte hain, jaise: <code>@MyChannel</code> ya <code>-100...</code>)</i>\n\n"
            "❌ Cancel karne ke liye <code>/cancel</code> likhein.",
            quote=True
        )

    @app.on_message(filters.command(["cancel", "cancel_fsub"]))
    async def cancel_fsub_cmd(client, message):
        if message.from_user and message.from_user.id in WAITING_FSUB_FORWARD:
            WAITING_FSUB_FORWARD.discard(message.from_user.id)
            await message.reply_text("❌ Force-Sub add process cancel ho gaya.", quote=True)

    @app.on_message(filters.private & ~filters.regex(r"^/") & filters.create(lambda _, __, m: bool(m.from_user and m.from_user.id in WAITING_FSUB_FORWARD)), group=1)
    async def fsub_forward_listener(client, message):
        """Listens for the forwarded channel message or channel username from the owner"""
        if not message.from_user:
            return
        user_id = message.from_user.id
        if user_id not in WAITING_FSUB_FORWARD:
            return

        if message.text and message.text.strip().lower() in ("/cancel", "cancel"):
            WAITING_FSUB_FORWARD.discard(user_id)
            await message.reply_text("❌ Force-Sub add process cancel ho gaya.", quote=True)
            return

        if message.text and message.text.startswith("/"):
            return

        target = None
        # Case 1: Forwarded message with channel header
        if message.forward_from_chat:
            target = message.forward_from_chat.id
        # Case 2: Owner pasted username or channel ID or t.me link
        elif message.text:
            text = message.text.strip()
            if text.startswith("@") or text.startswith("-100") or (text.startswith("-") and text[1:].isdigit()):
                target = int(text) if (text.startswith("-") and text[1:].isdigit()) else text
            elif text.isdigit():
                target = int(f"-100{text}")
            elif "t.me/" in text:
                import re
                m = re.search(r"t\.me/([A-Za-z0-9_]+)", text)
                if m:
                    target = f"@{m.group(1)}"

        if not target:
            await message.reply_text(
                "⚠️ <b>Channel Message Nahi Mila!</b>\n\n"
                "Kripya us channel se koi message <b>Forward</b> karein (Forward Tag on hona chahiye), ya fir direct username/ID bhejein jaise: <code>@MyChannel</code>.\n\n"
                "Cancel karne ke liye: <code>/cancel</code>",
                quote=True
            )
            return

        WAITING_FSUB_FORWARD.discard(user_id)
        await check_and_add_channel(client, message, target, message.from_user)

    def _build_fsubs_markup(channels):
        buttons = []
        for idx, ch in enumerate(channels, 1):
            ch_id = ch.get("raw") or ch.get("id")
            title = ch.get("title") or str(ch_id)
            buttons.append([
                InlineKeyboardButton(f"🗑️ Delete Channel {idx} ({title[:18]})", callback_data=f"delfsub_{ch_id}")
            ])
        buttons.append([
            InlineKeyboardButton("❌ Close Menu", callback_data="close_admin_menu")
        ])
        return InlineKeyboardMarkup(buttons)

    @app.on_message(filters.command(["delfsub", "remfsub", "removefsub", "del_fsub", "deletesub", "delchannel"]))
    async def del_fsub_cmd(client, message):
        """Remove a dynamic Force-Sub channel (interactive or direct)"""
        if not _is_owner_user(message.from_user):
            await message.reply_text("⛔ Owner / Admin only command.", quote=True)
            return

        from utils.force_sub import get_all_active_fsubs

        # Option A: Replied to a forwarded message from the channel
        if message.reply_to_message and message.reply_to_message.forward_from_chat:
            target_id = str(message.reply_to_message.forward_from_chat.id)
            target_title = message.reply_to_message.forward_from_chat.title or target_id
            db.del_fsub_channel(target_id)
            active = get_all_active_fsubs()
            await message.reply_text(
                f"🗑️ <b>Channel Removed Successfully!</b>\n\n"
                f"📢 <b>Channel:</b> {esc(target_title)}\n"
                f"🆔 <b>ID:</b> <code>{target_id}</code>\n\n"
                f"📋 Remaining Active Channels: <b>{len(active)}</b>\n"
                f"Active list dekhne ke liye: <code>/fsubs</code>",
                quote=True
            )
            return

        parts = message.text.split(maxsplit=1)
        # Option B: Direct argument given like /delfsub -1002194570573 or /delfsub @channel
        if len(parts) >= 2 and parts[1].strip():
            raw_ch = parts[1].strip()
            db.del_fsub_channel(raw_ch)
            active = get_all_active_fsubs()
            await message.reply_text(
                f"🗑️ <b>Channel Removed Successfully!</b>\n\n"
                f"Target: <code>{esc(raw_ch)}</code> ko Force-Sub list se hata diya gaya hai.\n\n"
                f"📋 Remaining Active Channels: <b>{len(active)}</b>\n"
                f"Active list dekhne ke liye: <code>/fsubs</code>",
                quote=True
            )
            return

        # Option C: No argument given -> show interactive 1-click delete menu!
        active = get_all_active_fsubs()
        if not active:
            await message.reply_text(
                "ℹ️ <b>Koi bhi Force-Sub channel added nahi hai.</b>\n\n"
                "Naya channel add karne ke liye: <code>/addfsub</code>",
                quote=True
            )
            return

        text = (
            "🗑️ <b>Delete Force-Sub Channel:</b>\n\n"
            "Aap jis channel ko remove karna chahte hain, niche diye gaye <b>Delete Button</b> par click karein:\n\n"
        )
        for i, ch in enumerate(active, 1):
            text += f"{i}️⃣ <b>{esc(ch.get('title') or str(ch.get('id')))}</b>\n"
            text += f"   • ID: <code>{ch.get('raw') or ch.get('id')}</code>\n\n"
        text += "💡 Ya direct command use karein: <code>/delfsub &lt;channel_id&gt;</code>"

        await message.reply_text(text, reply_markup=_build_fsubs_markup(active), quote=True)

    @app.on_message(filters.command(["fsubs", "forcesub", "channels", "forcesubs"]))
    async def list_fsubs_cmd(client, message):
        """View all active Force-Sub channels with 1-click delete buttons"""
        if not _is_owner_user(message.from_user):
            await message.reply_text("⛔ Owner / Admin only command.", quote=True)
            return

        from utils.force_sub import get_all_active_fsubs
        active = get_all_active_fsubs()
        if not active:
            await message.reply_text(
                "ℹ️ <b>Abhi koi bhi Force-Sub channel set nahi hai.</b>\n\n"
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
        text += "➖ <b>Remove Channel:</b> Niche diye gaye <b>Delete</b> button par click karein ya <code>/delfsub &lt;ID&gt;</code> karein."

        await message.reply_text(text, reply_markup=_build_fsubs_markup(active), quote=True)

    @app.on_callback_query(filters.regex(r"^delfsub_(.+)"))
    async def del_fsub_callback(client, cq):
        if not _is_owner_user(cq.from_user):
            await cq.answer("⛔ Only owner / admin can do this.", show_alert=True)
            return

        target_ch = cq.matches[0].group(1)
        db.del_fsub_channel(target_ch)

        await cq.answer("🗑️ Channel removed from Force-Sub!", show_alert=True)

        from utils.force_sub import get_all_active_fsubs
        active = get_all_active_fsubs()
        if not active:
            try:
                await cq.message.edit_text("ℹ️ <b>Sabhi Force-Sub channels remove ho gaye hain.</b>\n\nNaya channel add karne ke liye: <code>/addfsub</code>")
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

    @app.on_callback_query(filters.regex(r"^close_admin_menu$"))
    async def close_admin_menu_cb(client, cq):
        try:
            await cq.message.delete()
        except Exception:
            await cq.answer()
            pass

    @app.on_message(filters.command(["admin", "owner", "panel", "control"]))
    async def owner_panel_cmd(client, message):
        if not _is_owner_user(message.from_user):
            await message.reply_text("⛔ <b>Access Denied:</b> This command is only for bot owners.", quote=True)
            return

        await ensure_owner_commands(client, message.chat.id)
        panel_text = get_owner_panel_text(message.from_user)
        panel_kb = get_owner_panel_markup()

        await message.reply_text(panel_text, reply_markup=panel_kb, quote=True)

    @app.on_callback_query(filters.regex(r"^(open_owner_panel|back_to_owner_panel)$"))
    async def open_owner_panel_cb(client, cq):
        if not _is_owner_user(cq.from_user):
            await cq.answer("⛔ Only owner can access this panel.", show_alert=True)
            return

        await cq.answer()
        if cq.message and cq.message.chat:
            await ensure_owner_commands(client, cq.message.chat.id)

        panel_text = get_owner_panel_text(cq.from_user)
        panel_kb = get_owner_panel_markup()

        try:
            if cq.message.photo:
                await cq.message.edit_caption(caption=panel_text, reply_markup=panel_kb)
            else:
                await cq.message.edit_text(text=panel_text, reply_markup=panel_kb)
        except Exception:
            await cq.message.reply_text(panel_text, reply_markup=panel_kb)

    @app.on_callback_query(filters.regex(r"^owner_action_broadcast$"))
    async def owner_action_broadcast_cb(client, cq):
        if not _is_owner_user(cq.from_user): return await cq.answer("⛔ Access denied", show_alert=True)
        await cq.answer()
        text = (
            "📢 <b>Broadcast Message Guide:</b>\n\n"
            "Bot ke sabhi users ko message ya photo bhejne ke 2 tarike hain:\n\n"
            "1️⃣ <b>Direct Command:</b>\n"
            "<code>/broadcast Aapka Sandesh</code>\n\n"
            "2️⃣ <b>Reply to Message:</b>\n"
            "Kisi bhi text, photo, ya video message par reply karein aur likhein: <code>/broadcast</code>\n\n"
            "• Running broadcast ko rokne ke liye: <code>/cancelbroadcast</code>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="back_to_owner_panel")]
        ])
        try:
            if cq.message.photo: await cq.message.edit_caption(caption=text, reply_markup=kb)
            else: await cq.message.edit_text(text=text, reply_markup=kb)
        except Exception: pass

    @app.on_callback_query(filters.regex(r"^owner_action_bpin$"))
    async def owner_action_bpin_cb(client, cq):
        if not _is_owner_user(cq.from_user): return await cq.answer("⛔ Access denied", show_alert=True)
        await cq.answer()
        text = (
            "📌 <b>Broadcast & Pin Guide:</b>\n\n"
            "Message ko broadcast karne ke sath har user ke chat me <b>Pin</b> karne ke liye:\n\n"
            "1️⃣ <b>Direct Command:</b>\n"
            "<code>/broadcast_pin Aapka Sandesh</code>\n\n"
            "2️⃣ <b>Reply to Message:</b>\n"
            "Message par reply karke likhein: <code>/broadcast_pin</code>\n\n"
            "• Pin hatane ke liye: <code>/unpin</code> ya <code>/unpinall</code>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="back_to_owner_panel")]
        ])
        try:
            if cq.message.photo: await cq.message.edit_caption(caption=text, reply_markup=kb)
            else: await cq.message.edit_text(text=text, reply_markup=kb)
        except Exception: pass

    @app.on_callback_query(filters.regex(r"^owner_action_addfsub$"))
    async def owner_action_addfsub_cb(client, cq):
        if not _is_owner_user(cq.from_user): return await cq.answer("⛔ Access denied", show_alert=True)
        await cq.answer()
        WAITING_FSUB_FORWARD.add(cq.from_user.id)
        text = (
            "➕ <b>Add Force-Sub Channel:</b>\n\n"
            "1️⃣ Pehle bot ko apne Channel me <b>Administrator</b> banayein.\n"
            "2️⃣ Uske baad us channel se <b>koi bhi message yahan Forward karein</b>!\n\n"
            "Ya fir direct command se add karein:\n"
            "<code>/addfsub &lt;channel_id ya @username&gt;</code>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="back_to_owner_panel")]
        ])
        try:
            if cq.message.photo: await cq.message.edit_caption(caption=text, reply_markup=kb)
            else: await cq.message.edit_text(text=text, reply_markup=kb)
        except Exception: pass

    @app.on_callback_query(filters.regex(r"^owner_action_delfsub$"))
    async def owner_action_delfsub_cb(client, cq):
        if not _is_owner_user(cq.from_user): return await cq.answer("⛔ Access denied", show_alert=True)
        await cq.answer()
        from utils.force_sub import get_all_active_fsubs
        active = get_all_active_fsubs()
        if not active:
            text = "ℹ️ <b>Abhi koi bhi active Force-Sub channel nahi hai.</b>"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="back_to_owner_panel")]])
        else:
            text = "🗑️ <b>Delete Channel — Select to Remove:</b>\n\nJis channel ko hatana ho, uska button dabayein:"
            buttons = []
            for idx, ch in enumerate(active, 1):
                ch_id = ch.get("raw") or ch.get("id")
                title = ch.get("title") or str(ch_id)
                buttons.append([InlineKeyboardButton(f"🗑️ Delete Channel {idx} ({title[:18]})", callback_data=f"delfsub_{ch_id}")])
            buttons.append([InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="back_to_owner_panel")])
            kb = InlineKeyboardMarkup(buttons)
        try:
            if cq.message.photo: await cq.message.edit_caption(caption=text, reply_markup=kb)
            else: await cq.message.edit_text(text=text, reply_markup=kb)
        except Exception: pass

    @app.on_callback_query(filters.regex(r"^owner_action_listfsub$"))
    async def owner_action_listfsub_cb(client, cq):
        if not _is_owner_user(cq.from_user): return await cq.answer("⛔ Access denied", show_alert=True)
        await cq.answer()
        from utils.force_sub import get_all_active_fsubs
        active = get_all_active_fsubs()
        if not active:
            text = "ℹ️ <b>Abhi koi bhi Force-Sub channel set nahi hai.</b>\n\nNaya channel add karne ke liye: <code>/addfsub</code>"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="back_to_owner_panel")]])
        else:
            text = "📢 <b>Active Force-Sub Channels List:</b>\n\n"
            for i, ch in enumerate(active, 1):
                text += f"{i}️⃣ <b>{esc(ch['title'])}</b>\n"
                text += f"   • ID: <code>{ch.get('raw') or ch.get('id')}</code>\n"
                text += f"   • Link: {ch.get('url') or 'N/A'}\n\n"
            buttons = []
            for idx, ch in enumerate(active, 1):
                ch_id = ch.get("raw") or ch.get("id")
                buttons.append([InlineKeyboardButton(f"🗑️ Delete Channel {idx}", callback_data=f"delfsub_{ch_id}")])
            buttons.append([InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="back_to_owner_panel")])
            kb = InlineKeyboardMarkup(buttons)
        try:
            if cq.message.photo: await cq.message.edit_caption(caption=text, reply_markup=kb)
            else: await cq.message.edit_text(text=text, reply_markup=kb)
        except Exception: pass

    @app.on_callback_query(filters.regex(r"^owner_action_admins$"))
    async def owner_action_admins_cb(client, cq):
        if not _is_owner_user(cq.from_user): return await cq.answer("⛔ Access denied", show_alert=True)
        await cq.answer()
        admins = db.get_all_admins()
        text = "🛡️ <b>Bot Admins Management:</b>\n\n"
        if not admins:
            text += "• Koi custom admin add nahi kiya gaya hai.\n\n"
        else:
            for a_id, a_name, added_by in admins:
                text += f"• <code>{a_id}</code> | {esc(a_name)} (by {added_by})\n"
            text += "\n"
        text += (
            "➕ <b>Add Admin:</b> <code>/addadmin &lt;user_id ya reply&gt;</code>\n"
            "➖ <b>Remove Admin:</b> <code>/deladmin &lt;user_id ya reply&gt;</code>\n"
            "📋 <b>View Admins:</b> <code>/admins</code>"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="back_to_owner_panel")]])
        try:
            if cq.message.photo: await cq.message.edit_caption(caption=text, reply_markup=kb)
            else: await cq.message.edit_text(text=text, reply_markup=kb)
        except Exception: pass

    @app.on_callback_query(filters.regex(r"^owner_action_stats$"))
    async def owner_action_stats_cb(client, cq):
        if not _is_owner_user(cq.from_user): return await cq.answer("⛔ Access denied", show_alert=True)
        await cq.answer()
        u, c = db.stats()
        dl_count = db.total_downloads()
        from utils.force_sub import get_all_active_fsubs
        fsubs = get_all_active_fsubs()
        from plugins.start import START_TIME
        import time
        uptime_sec = int(time.time() - START_TIME)
        hours, rem = divmod(uptime_sec, 3600)
        minutes, seconds = divmod(rem, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"
        text = (
            f"📊 <b>Detailed Bot Statistics:</b>\n\n"
            f"• 👤 <b>Total Users:</b> <code>{u}</code>\n"
            f"• 👥 <b>Total Groups:</b> <code>{c}</code>\n"
            f"• 📥 <b>Total Downloads Served:</b> <code>{dl_count}</code>\n"
            f"• 📢 <b>Force-Sub Channels:</b> <code>{len(fsubs)}</code> active\n"
            f"• ⏱️ <b>Server Uptime:</b> <code>{uptime_str}</code>\n"
            f"• ⚡ <b>Engine:</b> 24/7 Running Active"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="back_to_owner_panel")]])
        try:
            if cq.message.photo: await cq.message.edit_caption(caption=text, reply_markup=kb)
            else: await cq.message.edit_text(text=text, reply_markup=kb)
        except Exception: pass

