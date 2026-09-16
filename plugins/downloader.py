import os, uuid, asyncio, traceback, time, subprocess, re
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from config import DOWNLOAD_DIR, SUPPORT_GROUP_URL, FORCE_SUB_CHANNEL, UPDATE_CHANNEL_URL
from utils.helpers import (
    bold, esc, human_size, progress_bar, Throttle,
    extract_instagram_links, is_private_chat, clean_instagram_url, is_reel_or_video_url
)
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

def _download_choice_markup_video(token):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 Video (Full HD)", callback_data=f"dl_full_{token}"),
        ],
        [
            InlineKeyboardButton("📹 MP4 Video (Mute)", callback_data=f"dl_vidonly_{token}"),
            InlineKeyboardButton("🎵 MP3 Audio Only", callback_data=f"dl_mp3_{token}"),
        ]
    ])

def _download_choice_markup_post(token):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📸 Download Post (Full HD)", callback_data=f"dl_full_{token}"),
        ],
        [
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

def _scan_media_files(out_dir):
    valid_exts = {".mp4", ".mov", ".mkv", ".webm", ".jpg", ".jpeg", ".png", ".webp"}
    items = []
    if not os.path.exists(out_dir):
        return items
    for fname in sorted(os.listdir(out_dir)):
        ext = os.path.splitext(fname)[1].lower()
        if ext in valid_exts:
            fp = os.path.join(out_dir, fname)
            if os.path.isfile(fp) and os.path.getsize(fp) > 0:
                is_vid = ext in {".mp4", ".mov", ".mkv", ".webm"}
                items.append((fp, is_vid))
    return items

async def _ytdlp_download(url, out_dir, loop, status, throttle, mode="full"):
    """
    Downloads via yt-dlp. Handles both single posts and multi-item carousels.
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

    out_tpl = os.path.join(out_dir, "%(autonumber)02d_%(id)s.%(ext)s")

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
            "noplaylist": False,
        }
    elif mode == "vidonly":
        opts = {
            "outtmpl": out_tpl,
            "format": "bestvideo/best[ext=mp4]/best",
            "progress_hooks": [hook],
            "quiet": True,
            "noplaylist": False,
        }
    else:  # full: video or photo or carousel
        opts = {
            "outtmpl": out_tpl,
            "format": "best[ext=mp4]/best",
            "progress_hooks": [hook],
            "quiet": True,
            "noplaylist": False,
        }

    def _dl():
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            caption = ""
            if info:
                caption = info.get("description") or info.get("title") or ""
                if not caption and info.get("entries"):
                    first_e = next((e for e in info["entries"] if e), None)
                    if first_e:
                        caption = first_e.get("description") or first_e.get("title") or ""
            files = _scan_media_files(out_dir)
            return files, caption

    return await loop.run_in_executor(None, _dl)

async def _instaloader_download(url, out_dir, loop, mode="full"):
    """
    Downloads via Instaloader. Explicitly checks for GraphSidecar / carousel
    and downloads every single photo and video in the post.
    """
    import requests, instaloader

    def _dl():
        sc = re.search(r"instagram\.com/(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)", url)
        if not sc:
            raise ValueError("Could not parse shortcode.")
        shortcode = sc.group(1)
        L = instaloader.Instaloader(
            dirname_pattern=out_dir,
            save_metadata=False,
            download_comments=False,
            download_geotags=False,
            download_video_thumbnails=False
        )
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        caption = post.caption or ""
        media_items = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        # Check if post is a sidecar (carousel album with multiple photos or videos)
        if post.typename == "GraphSidecar" or getattr(post, "mediacount", 1) > 1:
            try:
                nodes = list(post.get_sidecar_nodes())
            except Exception:
                nodes = []

            if nodes:
                for idx, node in enumerate(nodes, 1):
                    if node.is_video:
                        m_url = node.video_url
                        ext = "mp4"
                        is_vid = True
                    else:
                        m_url = node.display_url
                        ext = "jpg"
                        is_vid = False

                    fp = os.path.join(out_dir, f"{shortcode}_{idx:02d}.{ext}")
                    try:
                        r = requests.get(m_url, headers=headers, stream=True, timeout=60)
                        r.raise_for_status()
                        with open(fp, "wb") as f:
                            for chunk in r.iter_content(1024 * 256):
                                if chunk:
                                    f.write(chunk)
                        if os.path.exists(fp) and os.path.getsize(fp) > 0:
                            media_items.append((fp, is_vid))
                    except Exception:
                        pass

        # Fallback to single item if sidecar didn't yield files or not sidecar
        if not media_items:
            if post.is_video:
                m_url = post.video_url
                ext = "mp4"
                is_vid = True
            else:
                m_url = post.url
                ext = "jpg"
                is_vid = False

            fp = os.path.join(out_dir, f"{shortcode}_01.{ext}")
            r = requests.get(m_url, headers=headers, stream=True, timeout=60)
            r.raise_for_status()
            with open(fp, "wb") as f:
                for chunk in r.iter_content(1024 * 256):
                    if chunk:
                        f.write(chunk)
            if os.path.exists(fp) and os.path.getsize(fp) > 0:
                media_items.append((fp, is_vid))

        return media_items, caption

    return await loop.run_in_executor(None, _dl)

def _cleanup_old_cache():
    now = time.time()
    expired = [k for k, v in URL_CACHE.items() if now - v.get("time", 0) > 3600]
    for k in expired:
        URL_CACHE.pop(k, None)

async def ask_format_choice(client, message, raw_url):
    """Sends format selection buttons tailored to whether the URL is a Reel or a Post/Carousel."""
    _cleanup_old_cache()
    clean_url = clean_instagram_url(raw_url)
    is_reel = is_reel_or_video_url(clean_url)

    token = uuid.uuid4().hex[:12]
    URL_CACHE[token] = {
        "url": clean_url,
        "raw_url": raw_url,
        "user_id": message.from_user.id if message.from_user else 0,
        "user_name": message.from_user.first_name if message.from_user else "Friend",
        "time": time.time(),
        "chat_id": message.chat.id,
        "msg_id": message.id,
        "is_reel": is_reel
    }

    if is_reel:
        choice_text = (
            "🎬 <b>Select Download Format:</b>\n\n"
            "🔗 <b>Instagram Reel / Video Received!</b>\n"
            "Aapko ye media kis format me download karna hai? Niche diye gaye button par click karein:\n\n"
            "1️⃣ <b>Video (Full HD)</b> — Complete Reel/Video with sound\n"
            "2️⃣ <b>MP4 Video Only</b> — Video without audio (Muted)\n"
            "3️⃣ <b>MP3 Audio Only</b> — Extract Background Music/Audio\n\n"
            "───────────────\n"
            "💬 <b>Join Discussion Group:</b> @ash_movie_j"
        )
        markup = _download_choice_markup_video(token)
    else:
        choice_text = (
            "📸 <b>Select Download Format:</b>\n\n"
            "🔗 <b>Instagram Post Received!</b>\n"
            "Aapko ye post download karni hai? Niche diye gaye button par click karein:\n\n"
            "1️⃣ <b>Download Post (Full HD)</b> — All Photos / Videos in original HD\n"
            "2️⃣ <b>MP3 Audio Only</b> — Extract Background Music (if video post)\n\n"
            "───────────────\n"
            "💬 <b>Join Discussion Group:</b> @ash_movie_j"
        )
        markup = _download_choice_markup_post(token)

    await message.reply_text(
        choice_text,
        reply_markup=markup,
        quote=True
    )

async def execute_download(client, target_chat_id, reply_to_msg_id, user, url, mode, status_msg=None):
    """Executes the download, handling single photos, videos, and multi-post carousels."""
    clean_url = clean_instagram_url(url)
    is_reel = is_reel_or_video_url(clean_url)

    if mode == "mp3":
        initial_title = "🎵 MP3 Audio"
    elif is_reel:
        initial_title = "🎬 Video (Full HD)" if mode == "full" else "📹 MP4 Video (Mute)"
    else:
        initial_title = "📸 Post (Photos/Media)"

    status_text = f"⚡ <b>Processing {initial_title}...</b>\n<i>Please wait while I download and process your media.</i>"
    if not status_msg:
        status = await client.send_message(
            chat_id=target_chat_id,
            text=status_text,
            reply_to_message_id=reply_to_msg_id
        )
    else:
        status = status_msg
        await _safe_edit(status, status_text)

    loop = asyncio.get_event_loop()
    thr = Throttle(2.5)
    job_id = uuid.uuid4().hex[:10]
    out_dir = os.path.join(DOWNLOAD_DIR, job_id)
    os.makedirs(out_dir, exist_ok=True)
    media_items = []
    caption = ""

    try:
        # Step 1: Try yt-dlp with clean url
        try:
            media_items, caption = await _ytdlp_download(clean_url, out_dir, loop, status, thr, mode=mode)
        except Exception:
            media_items = []

        # Step 2: If yt-dlp returned nothing or for non-reels if only 1 item was found,
        # verify with instaloader to catch all photos in multi-post carousel
        if not media_items or (not is_reel and len(media_items) <= 1):
            try:
                await _safe_edit(status, "⚡ <i>Fetching full post media...</i>")
                insta_items, insta_caption = await _instaloader_download(clean_url, out_dir, loop, mode=mode)
                if len(insta_items) > len(media_items):
                    media_items = insta_items
                    if not caption:
                        caption = insta_caption
            except Exception:
                pass

        # Final check if files exist
        if not media_items:
            # Re-scan out_dir in case files were downloaded with other names
            media_items = _scan_media_files(out_dir)

        if not media_items:
            raise RuntimeError("Could not download media. The post may be private, restricted, or expired.")

        # If mode is vidonly, mute all video items with ffmpeg
        if mode == "vidonly":
            muted_items = []
            for fp, is_v in media_items:
                if is_v:
                    mute_fp = os.path.join(out_dir, f"muted_{os.path.basename(fp)}")
                    cmd = ["ffmpeg", "-y", "-i", fp, "-c:v", "copy", "-an", mute_fp]
                    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if proc.returncode == 0 and os.path.exists(mute_fp):
                        try: os.remove(fp)
                        except: pass
                        muted_items.append((mute_fp, True))
                    else:
                        muted_items.append((fp, True))
                else:
                    muted_items.append((fp, False))
            media_items = muted_items

        # If mode is mp3, extract audio from first video or convert audio
        if mode == "mp3":
            vid_files = [fp for fp, is_v in media_items if is_v]
            if vid_files:
                src_vid = vid_files[0]
                mp3_fp = os.path.join(out_dir, f"{job_id}.mp3")
                cmd = ["ffmpeg", "-y", "-i", src_vid, "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", mp3_fp]
                proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if proc.returncode == 0 and os.path.exists(mp3_fp):
                    media_items = [(mp3_fp, False)]
            else:
                # If no video found, check for existing mp3 or audio file
                audios = [fp for fp, _ in media_items if fp.lower().endswith((".mp3", ".m4a", ".aac", ".ogg"))]
                if audios:
                    media_items = [(audios[0], False)]

        total_items = len(media_items)

        # Determine dynamic format label according to actual content
        if mode == "mp3":
            format_label = "🎵 MP3 Audio Only"
            log_mode = "MP3 Audio"
        elif total_items > 1:
            all_photos = all(not is_v for _, is_v in media_items)
            all_videos = all(is_v for _, is_v in media_items)
            if all_photos:
                format_label = f"📸 Post ({total_items} Photos)"
                log_mode = f"Post ({total_items} Photos)"
            elif all_videos:
                format_label = f"🎬 Post ({total_items} Videos)"
                log_mode = f"Post ({total_items} Videos)"
            else:
                format_label = f"📸 Post ({total_items} Media Items)"
                log_mode = f"Post ({total_items} Mixed Media)"
        else:
            _, is_vid = media_items[0]
            if is_vid:
                if mode == "vidonly":
                    format_label = "📹 MP4 Video (Mute)"
                    log_mode = "MP4 Video (Mute)"
                else:
                    format_label = "🎬 Video (Full HD)"
                    log_mode = "Video (Full HD)"
            else:
                format_label = "🖼️ Photo"
                log_mode = "Photo"

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
            f"📦 <b>Format:</b> {format_label}\n"
            f"👤 <b>Requested by:</b> {user_mention}\n"
            f"📢 <b>Updates Channel:</b> @{FORCE_SUB_CHANNEL}\n"
            f"💬 <b>Discussion Group:</b> @ash_movie_j\n\n"
            "✨ <i>HD Quality • High Speed • Always Free</i>"
        )

        has_post_caption = bool(caption and caption.strip())
        reply_markup = _media_buttons(cap_token, has_post_caption)

        if mode == "mp3":
            # Send audio file
            await client.send_audio(
                chat_id=target_chat_id,
                audio=media_items[0][0],
                title="Instagram Audio",
                performer="Ash Insta Downloader",
                caption=media_caption,
                reply_markup=reply_markup,
                reply_to_message_id=reply_to_msg_id,
                progress=up_progress
            )
        elif total_items == 1:
            # Single photo or video
            fp, is_vid = media_items[0]
            if is_vid:
                await client.send_video(
                    chat_id=target_chat_id,
                    video=fp,
                    caption=media_caption,
                    reply_markup=reply_markup,
                    supports_streaming=True,
                    reply_to_message_id=reply_to_msg_id,
                    progress=up_progress
                )
            else:
                await client.send_photo(
                    chat_id=target_chat_id,
                    photo=fp,
                    caption=media_caption,
                    reply_markup=reply_markup,
                    reply_to_message_id=reply_to_msg_id,
                    progress=up_progress
                )
        else:
            # Multi-post carousel / album (Send all items in media group)
            for chunk_idx, i in enumerate(range(0, total_items, 10)):
                chunk = media_items[i:i+10]
                media_group = []
                for idx, (fpath, is_v) in enumerate(chunk):
                    cap = media_caption if (chunk_idx == 0 and idx == 0) else None
                    if is_v:
                        media_group.append(InputMediaVideo(media=fpath, caption=cap))
                    else:
                        media_group.append(InputMediaPhoto(media=fpath, caption=cap))

                await client.send_media_group(
                    chat_id=target_chat_id,
                    media=media_group,
                    reply_to_message_id=reply_to_msg_id
                )

            # Send confirmation and interactive buttons below the media group
            await client.send_message(
                chat_id=target_chat_id,
                reply_to_message_id=reply_to_msg_id,
                text=f"✨ <b>{format_label} Download Completed!</b>",
                reply_markup=reply_markup
            )

        try:
            await status.delete()
        except Exception:
            pass

        # Record download in DB
        try:
            db.record_download(user.id if user else 0)
        except Exception:
            pass

        # Send download event to Log Channel
        try:
            await log_download(client, user, log_mode, url)
        except Exception:
            pass

    except Exception as e:
        traceback.print_exc()
        await _safe_edit(
            status,
            f"❌ <b>Failed to download media.</b>\n\n"
            f"This can happen with private accounts or expired stories.\n"
            f"<code>Error: {esc(str(e))[:200]}</code>\n\n"
            f"💬 <b>Discussion Group:</b> @ash_movie_j"
        )
    finally:
        try:
            for f in os.listdir(out_dir):
                try: os.remove(os.path.join(out_dir, f))
                except: pass
            if os.path.isdir(out_dir):
                os.rmdir(out_dir)
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

        await cq.answer("⏳ Starting download...")
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
