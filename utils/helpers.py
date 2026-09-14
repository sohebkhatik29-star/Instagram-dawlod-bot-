import re, html, time

INSTAGRAM_REGEX = re.compile(
    r"(https?://(?:www\.)?instagram\.com/(?:reel|reels|p|tv|stories)/[^\s?#]+[^\s]*)",
    re.IGNORECASE,
)

def bold(text): return f"<b>{text}</b>"
def esc(text):  return html.escape(str(text))

def is_private_chat(message_or_chat):
    chat = getattr(message_or_chat, "chat", message_or_chat)
    ctype = getattr(chat, "type", None)
    if not ctype:
        return False
    c_str = str(ctype).lower()
    return "private" in c_str

def is_group_chat(message_or_chat):
    return not is_private_chat(message_or_chat)

def extract_instagram_links(text):
    if not text: return []
    return INSTAGRAM_REGEX.findall(text)

def human_size(n):
    if not n: return "0 B"
    for u in ["B","KB","MB","GB"]:
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"

def progress_bar(pct, length=14):
    pct = max(0.0, min(100.0, pct))
    f = int(length * pct / 100)
    return f"[{'█'*f}{'░'*(length-f)}] {pct:5.1f}%"

class Throttle:
    def __init__(self, interval=2.5):
        self.interval = interval
        self._last = 0.0
    def ready(self):
        now = time.time()
        if now - self._last >= self.interval:
            self._last = now
            return True
        return False
