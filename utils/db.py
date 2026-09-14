import sqlite3, threading
from config import DATABASE_FILE

_lock = threading.Lock()
_conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
_conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT)")
_conn.execute("CREATE TABLE IF NOT EXISTS chats (chat_id INTEGER PRIMARY KEY, title TEXT)")
_conn.execute("CREATE TABLE IF NOT EXISTS warns (chat_id INTEGER, user_id INTEGER, count INTEGER DEFAULT 0, PRIMARY KEY(chat_id, user_id))")
_conn.execute("CREATE TABLE IF NOT EXISTS force_sub_channels (channel_id TEXT PRIMARY KEY, title TEXT, invite_link TEXT)")
_conn.execute("CREATE TABLE IF NOT EXISTS downloads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
_conn.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, username TEXT, added_by INTEGER)")
_conn.execute("CREATE TABLE IF NOT EXISTS pinned_broadcasts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, msg_id INTEGER, owner_msg_id INTEGER)")
_conn.commit()

def record_download(user_id):
    with _lock:
        try:
            _conn.execute("INSERT INTO downloads (user_id) VALUES (?)", (user_id,))
            _conn.commit()
        except Exception:
            pass

def total_downloads():
    with _lock:
        try:
            return _conn.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
        except Exception:
            return 0

def add_fsub_channel(channel_id, title, invite_link):
    with _lock:
        target = str(channel_id).strip()
        _conn.execute("CREATE TABLE IF NOT EXISTS disabled_fsubs (channel_id TEXT PRIMARY KEY)")
        _conn.execute("DELETE FROM disabled_fsubs WHERE channel_id=?", (target,))
        if target.startswith("@"):
            _conn.execute("DELETE FROM disabled_fsubs WHERE channel_id=?", (target[1:],))
        else:
            _conn.execute("DELETE FROM disabled_fsubs WHERE channel_id=?", (f"@{target}",))
        _conn.execute("INSERT INTO force_sub_channels VALUES(?,?,?) ON CONFLICT(channel_id) DO UPDATE SET title=excluded.title,invite_link=excluded.invite_link", (target, title or "", invite_link or ""))
        _conn.commit()

def del_fsub_channel(channel_id):
    with _lock:
        target = str(channel_id).strip()
        _conn.execute("CREATE TABLE IF NOT EXISTS disabled_fsubs (channel_id TEXT PRIMARY KEY)")
        _conn.execute("INSERT OR IGNORE INTO disabled_fsubs VALUES (?)", (target,))
        _conn.execute("DELETE FROM force_sub_channels WHERE channel_id=?", (target,))
        if target.startswith("-100"):
            _conn.execute("DELETE FROM force_sub_channels WHERE channel_id=?", (target[4:],))
            _conn.execute("INSERT OR IGNORE INTO disabled_fsubs VALUES (?)", (target[4:],))
        elif target.isdigit():
            _conn.execute("DELETE FROM force_sub_channels WHERE channel_id=?", (f"-100{target}",))
            _conn.execute("INSERT OR IGNORE INTO disabled_fsubs VALUES (?)", (f"-100{target}",))
        if target.startswith("@"):
            clean = target[1:]
            _conn.execute("DELETE FROM force_sub_channels WHERE channel_id=?", (clean,))
            _conn.execute("DELETE FROM force_sub_channels WHERE invite_link LIKE ?", (f"%{clean}%",))
            _conn.execute("INSERT OR IGNORE INTO disabled_fsubs VALUES (?)", (clean,))
        else:
            _conn.execute("DELETE FROM force_sub_channels WHERE channel_id=?", (f"@{target}",))
            _conn.execute("DELETE FROM force_sub_channels WHERE invite_link LIKE ?", (f"%{target}%",))
            _conn.execute("INSERT OR IGNORE INTO disabled_fsubs VALUES (?)", (f"@{target}",))
        _conn.commit()

def get_disabled_fsubs():
    with _lock:
        try:
            _conn.execute("CREATE TABLE IF NOT EXISTS disabled_fsubs (channel_id TEXT PRIMARY KEY)")
            return [r[0] for r in _conn.execute("SELECT channel_id FROM disabled_fsubs").fetchall()]
        except Exception:
            return []

def get_all_fsub_channels():
    with _lock:
        return _conn.execute("SELECT channel_id, title, invite_link FROM force_sub_channels").fetchall()

def add_user(user_id, username, first_name):
    with _lock:
        row = _conn.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,)).fetchone()
        is_new = row is None
        _conn.execute("INSERT INTO users VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name", (user_id, username or "", first_name or ""))
        _conn.commit()
        return is_new

def add_chat(chat_id, title):
    with _lock:
        _conn.execute("INSERT INTO chats VALUES(?,?) ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title", (chat_id, title or ""))
        _conn.commit()

def all_users():
    with _lock:
        return [r[0] for r in _conn.execute("SELECT user_id FROM users").fetchall()]

def all_chats():
    with _lock:
        return [r[0] for r in _conn.execute("SELECT chat_id FROM chats").fetchall()]

def stats():
    with _lock:
        u = _conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        c = _conn.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
        return u, c

def add_warn(chat_id, user_id):
    with _lock:
        _conn.execute("INSERT INTO warns VALUES(?,?,1) ON CONFLICT(chat_id,user_id) DO UPDATE SET count=count+1", (chat_id, user_id))
        _conn.commit()
        return _conn.execute("SELECT count FROM warns WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()[0]

def reset_warn(chat_id, user_id):
    with _lock:
        _conn.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        _conn.commit()

def get_warn(chat_id, user_id):
    with _lock:
        r = _conn.execute("SELECT count FROM warns WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
        return r[0] if r else 0

def add_admin(user_id, username="", added_by=0):
    with _lock:
        try:
            _conn.execute(
                "INSERT INTO admins (user_id, username, added_by) VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username",
                (int(user_id), username or "", int(added_by))
            )
            _conn.commit()
            return True
        except Exception:
            return False

def del_admin(user_id):
    with _lock:
        try:
            _conn.execute("DELETE FROM admins WHERE user_id=?", (int(user_id),))
            _conn.commit()
            return True
        except Exception:
            return False

def is_db_admin(user_id):
    with _lock:
        try:
            row = _conn.execute("SELECT 1 FROM admins WHERE user_id=?", (int(user_id),)).fetchone()
            return row is not None
        except Exception:
            return False

def get_all_admins():
    with _lock:
        try:
            return _conn.execute("SELECT user_id, username, added_by FROM admins").fetchall()
        except Exception:
            return []

def record_pinned_broadcast(user_id, msg_id, owner_msg_id):
    with _lock:
        try:
            _conn.execute(
                "INSERT INTO pinned_broadcasts (user_id, msg_id, owner_msg_id) VALUES (?,?,?)",
                (int(user_id), int(msg_id), int(owner_msg_id))
            )
            _conn.commit()
        except Exception:
            pass

def get_pinned_broadcasts(owner_msg_id=None):
    with _lock:
        try:
            if owner_msg_id:
                return _conn.execute("SELECT user_id, msg_id FROM pinned_broadcasts WHERE owner_msg_id=?", (int(owner_msg_id),)).fetchall()
            return _conn.execute("SELECT user_id, msg_id FROM pinned_broadcasts").fetchall()
        except Exception:
            return []

def delete_pinned_broadcasts(owner_msg_id=None):
    with _lock:
        try:
            if owner_msg_id:
                _conn.execute("DELETE FROM pinned_broadcasts WHERE owner_msg_id=?", (int(owner_msg_id),))
            else:
                _conn.execute("DELETE FROM pinned_broadcasts")
            _conn.commit()
        except Exception:
            pass

