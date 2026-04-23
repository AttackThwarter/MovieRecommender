import sqlite3

def init_db():
    """ایجاد دیتابیس با ساختار جدید (پشتیبانی از چند چت و فیدبک)"""
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT,
            role TEXT,
            content TEXT,
            feedback INTEGER DEFAULT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_message(session_id, username, role, content):
    """ذخیره پیام و برگرداندن ID آن برای ثبت فیدبک در آینده"""
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (session_id, username, role, content) VALUES (?, ?, ?, ?)",
        (session_id, username, role, content)
    )
    message_id = cursor.lastrowid # گرفتن آیدی پیامی که همین الان ذخیره شد
    conn.commit()
    conn.close()
    return message_id

def load_messages(session_id):
    """بارگذاری پیام‌های یک چت خاص"""
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, role, content, feedback FROM chat_history WHERE session_id = ? ORDER BY id ASC",
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    # حالا آیدی و فیدبک را هم به استریم‌لیت پاس می‌دهیم
    return [{"id": r[0], "role": r[1], "content": r[2], "feedback": r[3]} for r in rows]

def get_user_sessions(username):
    """گرفتن لیست تمام چت‌های یک کاربر"""
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    # گرفتن شناسه‌های یکتا بر اساس جدیدترین زمان
    cursor.execute(
        "SELECT DISTINCT session_id FROM chat_history WHERE username = ? ORDER BY timestamp DESC",
        (username,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def delete_session(session_id):
    """پاک کردن کامل یک چت"""
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def update_feedback(message_id, feedback_value):
    """ثبت لایک یا دیس‌لایک برای یک پیام مشخص در دیتابیس"""
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE chat_history SET feedback = ? WHERE id = ?", (feedback_value, message_id))
    conn.commit()
    conn.close()