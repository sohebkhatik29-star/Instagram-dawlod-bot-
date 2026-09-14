import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import RPCError
from utils.helpers import bold
from utils import db
from config import OWNER_IDS, SUDO_USERS

def _is_admin(user_id):
    if not user_id:
        return False
    if user_id in (OWNER_IDS + SUDO_USERS):
        return True
    return db.is_db_admin(user_id)

def _is_owner(user_id):
    return bool(user_id and user_id in (OWNER_IDS + SUDO_USERS))

async def _execute_broadcast(client, message, target_msg, do_pin=False):
    users = db.all_users()
    if not users:
        await message.reply_text(bold("⚠️ No users found in database to broadcast to."), quote=True)
        return

    mode_title = "Broadcast & Pin" if do_pin else "Broadcast"
    status = await message.reply_text(bold(f"⏳ Starting {mode_title} to {len(users)} users..."), quote=True)
    
    sent = 0
    pinned = 0
    failed = 0
    total = len(users)

    for idx, uid in enumerate(users, 1):
        try:
            copied = await target_msg.copy(uid)
            sent += 1
            if do_pin:
                try:
                    await client.pin_chat_message(chat_id=uid, message_id=copied.id, disable_notification=False)
                    pinned += 1
                    db.record_pinned_broadcast(user_id=uid, msg_id=copied.id, owner_msg_id=target_msg.id)
                except Exception:
                    pass
        except RPCError:
            failed += 1
        except Exception:
            failed += 1

        # Periodic update every 25 users
        if idx % 25 == 0 or idx == total:
            try:
                await status.edit_text(
                    bold(
                        f"⏳ <b>{mode_title} in progress...</b>\n\n"
                        f"📊 <b>Progress:</b> <code>{idx}/{total}</code> ({(idx/total)*100:.0f}%)\n"
                        f"✅ <b>Sent:</b> <code>{sent}</code>\n"
                        f"❌ <b>Failed:</b> <code>{failed}</code>"
                    )
                )
            except Exception:
                pass

        await asyncio.sleep(0.04)

    if do_pin:
        res_text = (
            f"✅ <b>Broadcast & Pin Completed!</b>\n\n"
            f"👥 <b>Total Users:</b> <code>{total}</code>\n"
            f"📤 <b>Sent:</b> <code>{sent}</code>\n"
            f"📌 <b>Pinned:</b> <code>{pinned}</code>\n"
            f"❌ <b>Failed/Blocked:</b> <code>{failed}</code>"
        )
    else:
        res_text = (
            f"✅ <b>Broadcast Completed!</b>\n\n"
            f"👥 <b>Total Users:</b> <code>{total}</code>\n"
            f"📤 <b>Sent:</b> <code>{sent}</code>\n"
            f"❌ <b>Failed/Blocked:</b> <code>{failed}</code>"
        )
    await status.edit_text(bold(res_text))

def register(app):

    # 1. /broadcast (or /bc)
    @app.on_message(filters.command(["broadcast", "bc"]))
    async def broadcast_cmd(client, message):
        if not _is_admin(message.from_user.id if message.from_user else 0):
            await message.reply_text(bold("⛔ Access Denied: Owner/Admin only."), quote=True)
            return

        # If replied to any message
        if message.reply_to_message:
            await _execute_broadcast(client, message, message.reply_to_message, do_pin=False)
            return

        # If text argument provided directly after command
        if len(message.command) > 1:
            text_to_send = message.text.split(None, 1)[1]
            temp_msg = await message.reply_text(text_to_send)
            await _execute_broadcast(client, message, temp_msg, do_pin=False)
            try:
                await temp_msg.delete()
            except Exception:
                pass
            return

        await message.reply_text(
            bold(
                "📢 <b>Broadcast Command Guide:</b>\n\n"
                "1. <b>Reply to any message</b> (Text, Photo, Video, Sticker, Document) with:\n"
                "   <code>/broadcast</code>\n\n"
                "2. <b>Or type your text directly:</b>\n"
                "   <code>/broadcast Hello everyone! New updates available.</code>\n\n"
                "💡 <i>Tip: Use <code>/broadcast_pin</code> to automatically pin the message!</i>"
            ),
            quote=True
        )

    # 2. /broadcast_pin (or /bcp)
    @app.on_message(filters.command(["broadcast_pin", "bcp", "pin_broadcast"]))
    async def broadcast_pin_cmd(client, message):
        if not _is_admin(message.from_user.id if message.from_user else 0):
            await message.reply_text(bold("⛔ Access Denied: Owner/Admin only."), quote=True)
            return

        # If replied to any message
        if message.reply_to_message:
            await _execute_broadcast(client, message, message.reply_to_message, do_pin=True)
            return

        # If text argument provided directly after command
        if len(message.command) > 1:
            text_to_send = message.text.split(None, 1)[1]
            temp_msg = await message.reply_text(text_to_send)
            await _execute_broadcast(client, message, temp_msg, do_pin=True)
            try:
                await temp_msg.delete()
            except Exception:
                pass
            return

        await message.reply_text(
            bold(
                "📌 <b>Broadcast & Pin Command Guide:</b>\n\n"
                "1. <b>Reply to any message</b> with:\n"
                "   <code>/broadcast_pin</code>\n\n"
                "2. <b>Or type your text directly:</b>\n"
                "   <code>/broadcast_pin Important announcement for all members!</code>\n\n"
                "<i>This will send the message to all users and PIN it in their private chat.</i>"
            ),
            quote=True
        )

    # 3. /unpin
    @app.on_message(filters.private & filters.command(["unpin", "unpin_msg"]))
    async def unpin_cmd(client, message):
        if not _is_admin(message.from_user.id if message.from_user else 0):
            await message.reply_text(bold("⛔ Access Denied: Owner/Admin only."), quote=True)
            return

        if message.reply_to_message:
            reply_id = message.reply_to_message.id
            records = db.get_pinned_broadcasts(owner_msg_id=reply_id)
            if records:
                status = await message.reply_text(bold(f"⏳ Unpinning message from {len(records)} users..."), quote=True)
                unpinned = 0
                for uid, mid in records:
                    try:
                        await client.unpin_chat_message(chat_id=uid, message_id=mid)
                        unpinned += 1
                    except Exception:
                        pass
                    await asyncio.sleep(0.03)
                db.delete_pinned_broadcasts(owner_msg_id=reply_id)
                await status.edit_text(bold(f"✅ <b>Successfully unpinned message from {unpinned} users!</b>"))
                return

        all_pinned = db.get_pinned_broadcasts()
        if all_pinned:
            status = await message.reply_text(bold(f"⏳ Unpinning last broadcast from {len(all_pinned)} users..."), quote=True)
            unpinned = 0
            for uid, mid in all_pinned:
                try:
                    await client.unpin_chat_message(chat_id=uid, message_id=mid)
                    unpinned += 1
                except Exception:
                    pass
                await asyncio.sleep(0.03)
            db.delete_pinned_broadcasts()
            await status.edit_text(bold(f"✅ <b>Successfully unpinned message from {unpinned} users!</b>"))
        else:
            await message.reply_text(
                bold(
                    "ℹ️ <b>How to Unpin:</b>\n\n"
                    "• Reply to the broadcasted message with <code>/unpin</code> to unpin it from all users.\n"
                    "• Or use <code>/unpinall</code> to unpin ALL pinned messages from all users."
                ),
                quote=True
            )

    # 4. /unpinall
    @app.on_message(filters.command(["unpinall", "unpin_all"]))
    async def unpinall_cmd(client, message):
        if not _is_admin(message.from_user.id if message.from_user else 0):
            await message.reply_text(bold("⛔ Access Denied: Owner/Admin only."), quote=True)
            return

        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes, Unpin All", callback_data="confirm_unpinall_yes"),
                InlineKeyboardButton("❌ Cancel", callback_data="confirm_unpinall_no")
            ]
        ])
        await message.reply_text(
            bold(
                "⚠️ <b>Are you sure you want to UNPIN ALL messages from all users?</b>\n\n"
                "<i>This will remove all pinned announcement messages in all user private chats.</i>"
            ),
            reply_markup=kb,
            quote=True
        )

    @app.on_callback_query(filters.regex("^confirm_unpinall_"))
    async def unpinall_callback(client, cq):
        if not _is_admin(cq.from_user.id if cq.from_user else 0):
            await cq.answer("⛔ Access Denied.", show_alert=True)
            return

        action = cq.data.split("_")[-1]
        if action == "no":
            await cq.answer("Cancelled.")
            await cq.message.edit_text(bold("❌ <b>Unpin All operation was cancelled.</b>"))
            return

        await cq.answer("Unpinning all messages...")
        await cq.message.edit_text(bold("⏳ <b>Unpinning all messages for every user in background...</b>"))
        users = db.all_users()
        unpinned_count = 0
        for uid in users:
            try:
                await client.unpin_all_chat_messages(chat_id=uid)
                unpinned_count += 1
            except Exception:
                pass
            await asyncio.sleep(0.03)

        db.delete_pinned_broadcasts()
        await cq.message.edit_text(
            bold(f"✅ <b>Successfully unpinned all messages from {unpinned_count} users!</b>")
        )

    # 5. /admins
    @app.on_message(filters.command("admins"))
    async def admins_cmd(client, message):
        if not _is_admin(message.from_user.id if message.from_user else 0):
            await message.reply_text(bold("⛔ Access Denied: Owner/Admin only."), quote=True)
            return

        owner_lines = "\n".join([f"• <code>{oid}</code>" for oid in (OWNER_IDS + SUDO_USERS)])
        db_admins = db.get_all_admins()
        if db_admins:
            admin_lines = "\n".join([f"• <code>{aid}</code> (@{un})" if un else f"• <code>{aid}</code>" for aid, un, _ in db_admins])
        else:
            admin_lines = "<i>No additional admins added yet.</i>"

        text = (
            f"🛡️ <b>Bot Administration Panel</b>\n\n"
            f"👑 <b>Bot Owners / Super Admins:</b>\n{owner_lines}\n\n"
            f"👮 <b>Custom Admins:</b>\n{admin_lines}\n\n"
            f"<b>Commands:</b>\n"
            f"• <code>/addadmin &lt;user_id&gt;</code> (Owner only)\n"
            f"• <code>/deladmin &lt;user_id&gt;</code> (Owner only)"
        )
        await message.reply_text(bold(text), quote=True)

    # 6. /addadmin
    @app.on_message(filters.command("addadmin"))
    async def add_admin_cmd(client, message):
        if not _is_owner(message.from_user.id if message.from_user else 0):
            await message.reply_text(bold("⛔ Access Denied: Only Bot Owner can add new admins."), quote=True)
            return

        target_id = None
        target_username = ""
        if message.reply_to_message and message.reply_to_message.from_user:
            target_id = message.reply_to_message.from_user.id
            target_username = message.reply_to_message.from_user.username or ""
        elif len(message.command) > 1 and message.command[1].isdigit():
            target_id = int(message.command[1])

        if not target_id:
            await message.reply_text(bold("Usage:\n• Reply to a user with <code>/addadmin</code>\n• Or: <code>/addadmin &lt;user_id&gt;</code>"), quote=True)
            return

        success = db.add_admin(target_id, target_username, message.from_user.id)
        if success:
            await message.reply_text(bold(f"✅ User <code>{target_id}</code> added as Bot Admin successfully!"), quote=True)
        else:
            await message.reply_text(bold("❌ Failed to add admin. Please try again."), quote=True)

    # 7. /deladmin
    @app.on_message(filters.command("deladmin"))
    async def del_admin_cmd(client, message):
        if not _is_owner(message.from_user.id if message.from_user else 0):
            await message.reply_text(bold("⛔ Access Denied: Only Bot Owner can remove admins."), quote=True)
            return

        target_id = None
        if message.reply_to_message and message.reply_to_message.from_user:
            target_id = message.reply_to_message.from_user.id
        elif len(message.command) > 1 and message.command[1].isdigit():
            target_id = int(message.command[1])

        if not target_id:
            await message.reply_text(bold("Usage:\n• Reply to a user with <code>/deladmin</code>\n• Or: <code>/deladmin &lt;user_id&gt;</code>"), quote=True)
            return

        success = db.del_admin(target_id)
        if success:
            await message.reply_text(bold(f"✅ User <code>{target_id}</code> removed from Bot Admins."), quote=True)
        else:
            await message.reply_text(bold("❌ User was not found in admin list."), quote=True)

    # 8. /gbroadcast
    @app.on_message(filters.command("gbroadcast"))
    async def gbroadcast_cmd(client, message):
        if not _is_admin(message.from_user.id if message.from_user else 0):
            await message.reply_text(bold("⛔ Access Denied: Owner/Admin only."), quote=True)
            return
        if not message.reply_to_message:
            await message.reply_text(bold("Reply to the message you want to broadcast to groups."), quote=True)
            return
        chats = db.all_chats()
        status = await message.reply_text(bold(f"Broadcasting to {len(chats)} groups..."), quote=True)
        sent = failed = 0
        for cid in chats:
            try:
                await message.reply_to_message.copy(cid)
                sent += 1
            except RPCError:
                failed += 1
            await asyncio.sleep(0.05)
        await status.edit_text(bold(f"Done!\nSent: {sent}\nFailed: {failed}"))
