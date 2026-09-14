import os, uuid, asyncio, traceback, time, subprocess
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DOWNLOAD_DIR, SUPPORT_GROUP_URL, FORCE_SUB_CHANNEL, UPDATE_CHANNEL_URL
from utils.helpers import bold, esc, human_size, progress_bar, Throttle, extract_instagram_links, is_private_chat
from utils.force_sub import is_subscribed, join_markup, join_text, get_unsubscribed_channels
from utils.logger import log_download
from utils import db

CAPTION_STORE = {}
URL_CACHE = {}  # token -> {"url": url, "user_id": user_id, "time": timestamp}

def _media_buttons(token, has_caption=True):
    buttons = []
    if has_caption:
        buttons.append([
            InlineKeyboardButton("📝 View Post Caption", callback_data=f"cap_{token}")
        ])
    buttons.append([
        InlineKeyboardButton("📢 Updates Channel", url=UPDATE_CHANNEL_URL),
        InlineKeyboardButton("💬 Discussion Group", url=SUPPORT_GROUP_URL)
    ])
    return InlineKeyboardMarkup(buttons)

def _download_choice_markup(token):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 Video + Audio (Full HD)", callback_data=f"dl_full_{token}"),
        ],
        [
            InlineKeyboardButton("📹 MP4 Video Only (Mute)", callback_data=f"dl_vidonly_{token}"),
            InlineKeyboardButton("🎵 MP3 Audio Only", callback_data=f"dl_mp3_{token}"),
        ]
    ])

async def _safe_edit(msg, text, reply_markup=None):
    try:
        if reply_markup is not None:
            await msg.edit_text(text, reply_markup=reply_markup)
        else:
            await msg.edit_text(text)
    except Exception:
        pass

async def _ytdlp_download(url, out_tpl, loop, status, throttle, mode="full"):
    """
    mode:
      - 'full': best video + best audio
      - 'vidonly': best video only (no audio)
      - 'mp3': extract audio only as mp3
    """
    import yt_dlp
    def hook(d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done  = d.get("downloaded_bytes", 0)
            pct   = (done/total*100) if total else 0
            if throttle.ready():
                text = (
                    f"⚡ <b>Downloading Instagram Media...</b>\n\n"
                    f"{progress_bar(pct)}\n"
                    f"📊 <b>Progress:</b> <code>{human_size(done)} / {human_size(total)}</code> ({pct:.1f}%)\n"
                    f"📢 <b>Updates:</b> @{FORCE_SUB_CHANNEL}"
                )
                asyncio.run_coroutine_threadsafe(_safe_edit(status, text), loop)

    if mode == "mp3":
        opts = {
            "outtmpl": out_tpl,
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "progress_hooks": [hook],
            "quiet": True,
            "noplaylist": True,
        }
    elif mode == "vidonly":
        opts = {
            "outtmpl": out_tpl,
            "format": "bestvideo/best[ext=mp4]/best",
            "progress_hooks": [hook],
            "quiet": True,
            "noplaylist": True,
        }
    else:  # full: video + audio
        opts = {
            "outtmpl": out_tpl,
            "format": "best[ext=mp4]/best",
            "progress_hooks": [hook],
            "quiet": True,
            "noplaylist": True,
        }

    def _dl():
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            caption = info.get("description") or info.get("title") or ""
            filename = ydl.prepare_filename(info)
            if mode == "mp3":
                base, _ = os.path.splitext(filename)
                mp3_file = base + ".mp3"
                if os.path.exists(mp3_file):
                    filename = mp3_file
            return filename, caption

    return await loop.run_in_executor(None, _dl)

async def _instaloader_fallback(url, out_dir, mode="full"):
    import re, requests, instaloader
    sc = re.search(r"instagram\.com/(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)", url)
    if not sc: raise ValueError("Could not parse shortcode.")
    L = instaloader.Instaloader(dirname_pattern=out_dir, save_metadata=False, download_comments=False)
    post = instaloader.Post.from_shortcode(L.context, sc.group(1))
    media_url = post.video_url if post.is_video else post.url
    ext = "mp4" if post.is_video else "jpg"
    fp = os.path.join(out_dir, f"{sc.group(1)}.{ext}")
    r = requests.get(media_url, stream=True, timeout=60); r.raise_for_status()
    with open(fp, "wb") as f:
        for chunk in r.iter_content(1024*256):
            if chunk: f.write(chunk)

    caption = post.caption or ""

    if post.is_video:
        if mode == "mp3":
            mp3_fp = os.path.join(out_dir, f"{sc.group(1)}.mp3")
            cmd = ["ffmpeg", "-y", "-i", fp, "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", mp3_fp]
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if proc.returncode == 0 and os.path.exists(mp3_fp):
                try: os.remove(fp)
                except: pass
                return mp3_fp, caption
        elif mode == "vidonly":
            mute_fp = os.path.join(out_dir, f"{sc.group(1)}_mute.mp4")
            cmd = ["ffmpeg", "-y", "-i", fp, "-c:v", "copy", "-an", mute_fp]
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if proc.returncode == 0 and os.path.exists(mute_fp):
                try: os.remove(fp)
                except: pass
                return mute_fp, caption

    return fp, caption

def _cleanup_old_cache():
    now = time.time()
    expired = [k for k, v in URL_CACHE.items() if now - v.get("time", 0) > 3600]
    for k in expired:
        URL_CACHE.pop(k, None)

async def ask_format_choice(client, message, url):
    """Sends choice buttons (Video+Audio, MP4 Video only, MP3 Audio only)"""
    _cleanup_old_cache()
    token = uuid.uuid4().hex[:12]
    URL_CACHE[token] = {
        "url": url,
        "user_id": message.from_user.id if message.from_user else 0,
        "user_name": message.from_user.first_name if message.from_user else "Friend",
        "time": time.time(),
        "chat_id": message.chat.id,
        "msg_id": message.id
    }

    choice_text = (
        "🎬 <b>Select Download Format:</b>\n\n"
        "🔗 <b>Instagram Link Received!</b>\n"
        "Aapko ye media kis format me download karna hai? Niche diye gaye button par click karein:\n\n"
        "1️⃣ <b>Video + Audio</b> — Complete Reel/Video with sound\n"
        "2️⃣ <b>MP4 Video Only</b> — Video without audio (Muted)\n"
        "3️⃣ <b>MP3 Audio Only</b> — Extract Background Music/Audio\n\n"
        "───────────────\n"
        "💬 <b>Join Discussion Group:</b> https://t.me/ash_movie_j"
    )

    await message.reply_text(
        choice_text,
        reply_markup=_download_choice_markup(token),
        quote=True
    )

async def execute_download(client, target_chat_id, reply_to_msg_id, user, url, mode, status_msg=None):
    """Executes the actual download based on mode: full | vidonly | mp3"""
    mode_labels = {
        "full": "🎬 Video + Audio (Full HD)",
        "vidonly": "📹 MP4 Video Only (Mute)",
        "mp3": "🎵 MP3 Audio Only"
    }
    mode_title = mode_labels.get(mode, "Media")

    if not status_msg:
        status = await client.send_message(
            chat_id=target_chat_id,
            text=f"⚡ <b>Processing {mode_title}...</b>\n<i>Please wait while I download and convert your media.</i>",
            reply_to_message_id=reply_to_msg_id
        )
    else:
        status = status_msg
        await _safe_edit(status, f"⚡ <b>Processing {mode_title}...</b>\n<i>Please wait while I download and convert your media.</i>")

    loop = asyncio.get_event_loop()
    thr = Throttle(2.5)
    job_id = uuid.uuid4().hex[:10]
    out_dir = os.path.join(DOWNLOAD_DIR, job_id)
    os.makedirs(out_dir, exist_ok=True)
    filepath = caption = None

    try:
        out_tpl = os.path.join(out_dir, "%(id)s.%(ext)s")
        try:
            filepath, caption = await _ytdlp_download(url, out_tpl, loop, status, thr, mode=mode)
        except Exception:
            await _safe_edit(status, "⚡ <i>Switching to fallback conversion engine...</i>")
            filepath, caption = await _instaloader_fallback(url, out_dir, mode=mode)

        # In case mode is vidonly and yt-dlp downloaded video with audio, mute with ffmpeg
        if mode == "vidonly" and filepath and filepath.lower().endswith((".mp4", ".mov", ".mkv", ".webm")):
            mute_path = os.path.join(out_dir, f"muted_{os.path.basename(filepath)}")
            cmd = ["ffmpeg", "-y", "-i", filepath, "-c:v", "copy", "-an", mute_path]
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if proc.returncode == 0 and os.path.exists(mute_path):
                try: os.remove(filepath)
                except: pass
                filepath = mute_path

        # If mode is mp3 and file isn't mp3 yet, convert it
        if mode == "mp3" and filepath and not filepath.lower().endswith(".mp3"):
            mp3_path = os.path.join(out_dir, f"{job_id}.mp3")
            cmd = ["ffmpeg", "-y", "-i", filepath, "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", mp3_path]
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if proc.returncode == 0 and os.path.exists(mp3_path):
                try: os.remove(filepath)
                except: pass
                filepath = mp3_path

        if not filepath or not os.path.exists(filepath):
            raise RuntimeError("Download finished but media file is missing.")

        cap_token = uuid.uuid4().hex[:12]
        CAPTION_STORE[cap_token] = caption.strip() if caption else "No caption."

        await _safe_edit(status, "📤 <b>Uploading to Telegram, almost done...</b>")
        up_thr = Throttle(2.5)

        async def up_progress(cur, tot):
            if up_thr.ready() or cur == tot:
                pct = (cur/tot*100) if tot else 0
                await _safe_edit(
                    status,
                    "📤 <b>Uploading to Telegram...</b>\n\n"
                    f"{progress_bar(pct)}\n"
                    f"📊 <b>Uploaded:</b> <code>{human_size(cur)} / {human_size(tot)}</code> ({pct:.1f}%)\n"
                    f"📢 <b>Updates:</b> @{FORCE_SUB_CHANNEL}"
                )

        if user:
            mention = getattr(user, "mention", None)
            if callable(mention):
                user_mention = user.mention(style="html")
            elif isinstance(mention, str):
                user_mention = mention
            else:
                user_mention = f'<a href="tg://user?id={user.id}">{esc(user.first_name or "Friend")}</a>'
        else:
            user_mention = "Friend"

        media_caption = (
            f"🎬 <b>Downloaded with Ash Insta Downloader Bot</b> ⚡\n\n"
            f"📦 <b>Format:</b> {mode_title}\n"
            f"👤 <b>Requested by:</b> {user_mention}\n"
            f"📢 <b>Updates Channel:</b> @{FORCE_SUB_CHANNEL}\n"
            f"💬 <b>Discussion Group:</b> @ash_movie_j\n\n"
            "✨ <i>HD Quality • High Speed • Always Free</i>"
        )

        has_post_caption = bool(caption and caption.strip())
        reply_markup = _media_buttons(cap_token, has_post_caption)

        is_audio = mode == "mp3" or filepath.lower().endswith((".mp3", ".m4a", ".aac", ".ogg", ".wav"))
        is_video = filepath.lower().endswith((".mp4", ".mov", ".mkv", ".webm"))

        kw = dict(
            chat_id=target_chat_id,
            reply_to_message_id=reply_to_msg_id,
            caption=media_caption,
            reply_markup=reply_markup,
            progress=up_progress
        )

        if is_audio:
            await client.send_audio(
                audio=filepath,
                title="Instagram Audio",
                performer="Ash Insta Downloader",
                **kw
            )
        elif is_video:
            await client.send_video(video=filepath, supports_streaming=True, **kw)
        else:
            await client.send_photo(photo=filepath, **kw)

        await status.delete()

        # Send download event to Log Channel
        try:
            await log_download(client, user, mode_title, url)
        except Exception:
            pass

    except Exception as e:
        traceback.print_exc()
        await _safe_edit(
            status,
            f"❌ <b>Failed to download {mode_title}.</b>\n\n"
            f"This can happen with private accounts or expired stories.\n"
            f"<code>Error: {esc(str(e))[:200]}</code>\n\n"
            f"💬 <b>Discussion Group:</b> @ash_movie_j"
        )
    finally:
        try:
            if filepath and os.path.exists(filepath): os.remove(filepath)
            for f in os.listdir(out_dir):
                try: os.remove(os.path.join(out_dir, f))
                except: pass
            if os.path.isdir(out_dir): os.rmdir(out_dir)
        except Exception:
            pass

def register(app):

    @app.on_message((filters.private | filters.group) & filters.text & ~filters.regex(r"^/"), group=2)
    async def link_listener(client, message):
        if not message.text or message.text.startswith("/"): return
        links = extract_instagram_links(message.text)
        if not links: return
        if is_private_chat(message):
            unjoined = await get_unsubscribed_channels(client, message.from_user.id)
            if unjoined:
                await message.reply_text(join_text(unjoined), reply_markup=join_markup(unjoined), quote=True)
                return
        for link in links[:3]:
            await ask_format_choice(client, message, link)

    @app.on_message(filters.command("dl"))
    async def dl_cmd(client, message):
        if len(message.command) < 2:
            await message.reply_text(bold("Usage: /dl <instagram link>"), quote=True)
            return
        if is_private_chat(message):
            unjoined = await get_unsubscribed_channels(client, message.from_user.id)
            if unjoined:
                await message.reply_text(join_text(unjoined), reply_markup=join_markup(unjoined), quote=True)
                return
        await ask_format_choice(client, message, message.command[1])

    @app.on_callback_query(filters.regex(r"^dl_(full|vidonly|mp3)_(.+)"))
    async def format_choice_cb(client, cq):
        mode, token = cq.matches[0].group(1), cq.matches[0].group(2)
        cached = URL_CACHE.get(token)
        if not cached:
            await cq.answer("⚠️ Link request expired or invalid! Please send the link again.", show_alert=True)
            return

        # Check Force Sub once more
        unjoined = await get_unsubscribed_channels(client, cq.from_user.id)
        if unjoined:
            await cq.answer("🔒 Please join all required channels first!", show_alert=True)
            await cq.message.reply_text(join_text(unjoined), reply_markup=join_markup(unjoined), quote=True)
            return

        await cq.answer(f"⏳ Starting {mode.upper()} download...")
        url = cached["url"]
        target_chat_id = cq.message.chat.id
        reply_to_msg_id = cached.get("msg_id") or cq.message.id
        user = cq.from_user

        await execute_download(
            client=client,
            target_chat_id=target_chat_id,
            reply_to_msg_id=reply_to_msg_id,
            user=user,
            url=url,
            mode=mode,
            status_msg=cq.message
        )

    @app.on_callback_query(filters.regex(r"^cap_"))
    async def show_caption(client, cq):
        token = cq.data.split("_", 1)[1]
        cap = CAPTION_STORE.get(token, "Caption no longer available.")
        if len(cap) > 900: cap = cap[:900] + "…"
        await cq.answer()
        await cq.message.reply_text(
            f"📝 <b>Original Instagram Post Caption:</b>\n\n"
            f"{esc(cap)}\n\n"
            "───────────────\n"
            "💬 <b>Discussion Group:</b> https://t.me/ash_movie_j",
            quote=True
        )
