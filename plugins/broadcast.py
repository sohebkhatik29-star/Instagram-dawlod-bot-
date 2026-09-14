import asyncio
from pyrogram import filters
from pyrogram.errors import RPCError
from utils.helpers import bold
from utils import db
from config import OWNER_IDS, SUDO_USERS

def _is_owner(uid): return uid in (OWNER_IDS + SUDO_USERS)

def register(app):

    @app.on_message(filters.command("broadcast"))
    async def broadcast_cmd(client, message):
        if not _is_owner(message.from_user.id):
            await message.reply_text(bold("Owner only."), quote=True); return
        if not message.reply_to_message:
            await message.reply_text(bold("Reply to the message you want to broadcast."), quote=True); return
        users = db.all_users()
        status = await message.reply_text(bold(f"Broadcasting to {len(users)} users..."), quote=True)
        sent = failed = 0
        for uid in users:
            try:
                await message.reply_to_message.copy(uid)
                sent += 1
            except RPCError:
                failed += 1
            await asyncio.sleep(0.05)
        await status.edit_text(bold(f"Done!\nSent: {sent}\nFailed: {failed}"))

    @app.on_message(filters.command("gbroadcast"))
    async def gbroadcast_cmd(client, message):
        if not _is_owner(message.from_user.id):
            await message.reply_text(bold("Owner only."), quote=True); return
        if not message.reply_to_message:
            await message.reply_text(bold("Reply to the message you want to broadcast."), quote=True); return
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
