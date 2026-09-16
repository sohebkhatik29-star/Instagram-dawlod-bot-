import os
import time
import subprocess
import uuid
from flask import Flask, jsonify, send_from_directory, request, Response

app = Flask(__name__, static_folder="web", static_url_path="")
START_TIME = time.time()
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route("/")
def index():
    if os.path.exists(os.path.join("web", "index.html")):
        return send_from_directory("web", "index.html")
    return jsonify({
        "status": "online",
        "bot": "Ash Insta Downloader Bot",
        "group": "https://t.me/ash_movie_j",
        "updates": "https://t.me/MoviesGroupG3"
    })

@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "uptime_seconds": int(time.time() - START_TIME),
        "bot_name": "Ash Insta Downloader Bot",
        "group": "https://t.me/ash_movie_j",
        "channel": "https://t.me/MoviesGroupG3"
    })

@app.route("/api/download", methods=["POST"])
def web_download():
    try:
        data = request.get_json(force=True, silent=True) or {}
        url  = data.get("url", "").strip()
        if not url or "instagram.com" not in url:
            return jsonify({"error": "Please provide a valid Instagram URL (reel, post, or story)"}), 400

        job_id  = uuid.uuid4().hex[:10]
        out_dir = os.path.join(DOWNLOAD_DIR, job_id)
        os.makedirs(out_dir, exist_ok=True)
        out_tpl = os.path.join(out_dir, "%(id)s.%(ext)s")

        result = subprocess.run(
            [
                "python3", "-m", "yt_dlp",
                "-o", out_tpl,
                "--format", "best[ext=mp4]/best",
                "--no-playlist",
                "-q", url
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        files = [f for f in os.listdir(out_dir) if os.path.isfile(os.path.join(out_dir, f))]
        if not files:
            return jsonify({"error": "Download failed. The post might be private or blocked by rate limits."}), 500

        filepath = os.path.join(out_dir, files[0])
        filename = files[0]
        mime = "video/mp4" if filename.endswith(".mp4") else "image/jpeg"

        def generate():
            with open(filepath, "rb") as f:
                while chunk := f.read(1024 * 256):
                    yield chunk
            try:
                os.remove(filepath)
                os.rmdir(out_dir)
            except Exception:
                pass

        return Response(
            generate(),
            mimetype=mime,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Download timed out. Please try again."}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _keep_alive_loop(port):
    import urllib.request
    time.sleep(30)
    while True:
        try:
            render_url = os.environ.get("RENDER_EXTERNAL_URL")
            url = f"{render_url}/health" if render_url else f"http://127.0.0.1:{port}/health"
            req = urllib.request.Request(url, headers={"User-Agent": "BotKeepAlive/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
        except Exception:
            pass
        time.sleep(600)

def run_web_server(port):
    import threading
    threading.Thread(target=_keep_alive_loop, args=(port,), daemon=True).start()
    app.run(host="0.0.0.0", port=port, threaded=True)
