import sqlite3

def init_db():
    """ایجاد دیتابیس با ساختار جدید شامل جدول پروفایل کاربران"""
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    
    # جدول چت‌ها
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
    
    # جدول جدید: پروفایل سلیقه کاربران
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            username TEXT PRIMARY KEY,
            profile_text TEXT,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_message(session_id, username, role, content):
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (session_id, username, role, content) VALUES (?, ?, ?, ?)",
        (session_id, username, role, content)
    )
    message_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return message_id

def load_messages(session_id):
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, role, content, feedback FROM chat_history WHERE session_id = ? ORDER BY id ASC",
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "role": r[1], "content": r[2], "feedback": r[3]} for r in rows]

def get_user_sessions(username):
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT session_id FROM chat_history WHERE username = ? ORDER BY timestamp DESC",
        (username,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def delete_session(session_id):
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def update_feedback(message_id, feedback_value):
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE chat_history SET feedback = ? WHERE id = ?", (feedback_value, message_id))
    conn.commit()
    conn.close()

# ==========================================
# توابع جدید برای مدیریت پروفایل سلیقه کاربر
# ==========================================
def save_user_profile(username, profile_text):
    """ذخیره یا بروزرسانی پروفایل سلیقه کاربر"""
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_profiles (username, profile_text, last_updated)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(username) DO UPDATE SET 
            profile_text = excluded.profile_text,
            last_updated = CURRENT_TIMESTAMP
    """, (username, profile_text))
    conn.commit()
    conn.close()

def get_user_profile(username):
    """خواندن پروفایل سلیقه کاربر"""
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT profile_text FROM user_profiles WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "هنوز سلیقه خاصی برای این کاربر ثبت نشده است."

def get_all_user_messages(username):
    """گرفتن تاریخچه پیام‌های کاربر برای تحلیل هوش مصنوعی"""
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    # گرفتن ۲۰ پیام آخر کاربر برای تحلیل رفتار او
    cursor.execute("SELECT role, content FROM chat_history WHERE username = ? AND role = 'user' ORDER BY timestamp DESC LIMIT 20", (username,))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]