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
        "bot": "Movies Instagram Downloader Bot",
        "owner": "@movies_1780",
        "updates": "https://t.me/MoviesGroupG3"
    })

@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "uptime_seconds": int(time.time() - START_TIME),
        "bot_name": "Movies Instagram Downloader",
        "owner": "@movies_1780",
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

def run_web_server(port):
    app.run(host="0.0.0.0", port=port, threaded=True)
