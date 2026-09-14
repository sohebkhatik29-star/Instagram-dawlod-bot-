import importlib, subprocess, sys

REQUIRED_PACKAGES = {
    "pyrogram": "pyrofork",
    "tgcrypto": "TgCrypto",
    "yt_dlp":   "yt-dlp",
    "instaloader": "instaloader",
    "flask":    "flask",
    "requests": "requests",
    "dotenv":   "python-dotenv",
    "PIL":      "Pillow",
}

def _install(pkg):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])
        return True
    except Exception as e:
        print(f"[AUTOINSTALL] Failed to install {pkg}: {e}")
        return False

def ensure_dependencies():
    print("[AUTOINSTALL] Checking deps... #RADHEY")
    for mod, pkg in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            print(f"[AUTOINSTALL] Installing {pkg}...")
            _install(pkg)
    print("[AUTOINSTALL] All good!\n")
