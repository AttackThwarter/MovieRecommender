import sqlite3

def init_db():
    """ایجاد دیتابیس و جدول پیام‌ها در صورتی که وجود نداشته باشند"""
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    # ساخت جدول: شناسه، نام کاربری، نقش (سیستم/کاربر/مدل) و متن پیام
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_message(username, role, content):
    """ذخیره یک پیام جدید در دیتابیس"""
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (username, role, content) VALUES (?, ?, ?)",
        (username, role, content)
    )
    conn.commit()
    conn.close()

def load_messages(username):
    """بارگذاری تمام پیام‌های یک کاربر خاص"""
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM chat_history WHERE username = ? ORDER BY id ASC",
        (username,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    # تبدیل خروجی دیتابیس به فرمت لیست دیکشنری که استریم‌لیت می‌فهمد
    return [{"role": r, "content": c} for r, c in rows]