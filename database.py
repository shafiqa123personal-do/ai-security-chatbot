import os
import sqlite3
from datetime import datetime

DB_NAME = "chatbot.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT DEFAULT '',
            is_admin INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            title TEXT NOT NULL,
            messages TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    admin_username = os.environ.get("ADMIN_USERNAME")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if admin_username and admin_password:
        from werkzeug.security import generate_password_hash
        try:
            conn.execute(
                "INSERT INTO users (username, password, email, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
                (admin_username, generate_password_hash(admin_password), "", 1, datetime.now().isoformat())
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass

    conn.close()


def create_user(username, hashed_password, email=""):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password, email, is_admin, created_at) VALUES (?, ?, ?, 0, ?)",
            (username, hashed_password, email, datetime.now().isoformat())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user(username):
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return user


def save_chat_log(username, title, messages_json):
    conn = get_connection()
    conn.execute(
        "INSERT INTO chat_logs (username, title, messages, created_at) VALUES (?, ?, ?, ?)",
        (username, title, messages_json, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_user_logs(username):
    conn = get_connection()
    logs = conn.execute(
        "SELECT id, title, created_at FROM chat_logs WHERE username = ? ORDER BY created_at DESC",
        (username,)
    ).fetchall()
    conn.close()
    return [dict(log) for log in logs]


def get_log_by_id(log_id, username=None):
    conn = get_connection()
    if username:
        log = conn.execute(
            "SELECT * FROM chat_logs WHERE id = ? AND username = ?",
            (log_id, username)
        ).fetchone()
    else:
        log = conn.execute(
            "SELECT * FROM chat_logs WHERE id = ?", (log_id,)
        ).fetchone()
    conn.close()
    return dict(log) if log else None


def delete_log(log_id, username=None):
    conn = get_connection()
    if username:
        conn.execute(
            "DELETE FROM chat_logs WHERE id = ? AND username = ?",
            (log_id, username)
        )
    else:
        conn.execute("DELETE FROM chat_logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()


def get_all_users():
    conn = get_connection()
    users = conn.execute(
        "SELECT id, username, is_admin, created_at FROM users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(u) for u in users]


def get_all_logs():
    conn = get_connection()
    logs = conn.execute(
        "SELECT id, username, title, created_at FROM chat_logs ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(log) for log in logs]


def delete_user(username):
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE username = ? AND is_admin = 0", (username,))
    conn.execute("DELETE FROM chat_logs WHERE username = ?", (username,))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_connection()
    total_users = conn.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0").fetchone()[0]
    total_chats = conn.execute("SELECT COUNT(*) FROM chat_logs").fetchone()[0]
    today = datetime.now().strftime("%Y-%m-%d")
    chats_today = conn.execute(
        "SELECT COUNT(*) FROM chat_logs WHERE created_at LIKE ?", (f"{today}%",)
    ).fetchone()[0]
    conn.close()
    return {
        "total_users": total_users,
        "total_chats": total_chats,
        "chats_today": chats_today
    }
