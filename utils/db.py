import sqlite3, threading
from config import DATABASE_FILE

_lock = threading.Lock()
_conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
_conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT)")
_conn.execute("CREATE TABLE IF NOT EXISTS chats (chat_id INTEGER PRIMARY KEY, title TEXT)")
_conn.execute("CREATE TABLE IF NOT EXISTS warns (chat_id INTEGER, user_id INTEGER, count INTEGER DEFAULT 0, PRIMARY KEY(chat_id, user_id))")
_conn.commit()

def add_user(user_id, username, first_name):
    with _lock:
        _conn.execute("INSERT INTO users VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name", (user_id, username or "", first_name or ""))
        _conn.commit()

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
