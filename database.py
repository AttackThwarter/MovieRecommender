import sqlite3
from datetime import datetime
import uuid

DB_PATH = "movies_app.db"

def init_db():
    """ساخت جداول دیتابیس در صورت عدم وجود"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # ساخت جدول پیام‌ها با فیلد فیدبک
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            username TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT,
            feedback TEXT
        )
    ''')
    
    # ساخت جدول پروفایل سلیقه کاربر
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            username TEXT PRIMARY KEY,
            taste TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def save_message(session_id, username, role, content):
    m_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (id, session_id, username, role, content, timestamp, feedback) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (m_id, session_id, username, role, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), None)
    )
    conn.commit()
    conn.close()
    return m_id

def load_messages(session_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, role, content, feedback FROM messages WHERE session_id = ? ORDER BY timestamp", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "role": r[1], "content": r[2], "feedback": r[3]} for r in rows]

def get_user_sessions(username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT session_id FROM messages WHERE username = ? ORDER BY session_id DESC", (username,))
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def delete_session(session_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def update_feedback(message_id, feedback):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE messages SET feedback = ? WHERE id = ?", (feedback, message_id))
    conn.commit()
    conn.close()

def save_user_profile(username, taste):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO profiles (username, taste) VALUES (?, ?)", (username, taste))
    conn.commit()
    conn.close()

def get_user_profile(username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT taste FROM profiles WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "هنوز سلیقه‌ای ثبت نشده است."

def get_all_user_messages(username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM messages WHERE username = ? AND role = 'user' ORDER BY timestamp ASC", (username,))
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_user_taste_from_ratings(username, limit=5):
    """آخرین فیلم‌های پیشنهاد شده و امتیاز کاربر به آن‌ها را استخراج می‌کند"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT content, feedback FROM messages 
        WHERE session_id IN (SELECT session_id FROM messages WHERE username = ?) 
        AND role = 'assistant' AND feedback IS NOT NULL
        ORDER BY timestamp DESC LIMIT ?
    ''', (username, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "کاربر هنوز به هیچ فیلمی امتیاز نداده است."

    liked_movies = []
    disliked_movies = []
    
    for content, feedback in rows:
        try:
            rating = int(feedback)
            movie_summary = content.split('\n')[0][:50] + "..." 
            
            if rating >= 4:
                liked_movies.append(f"امتیاز {rating} ستاره به: {movie_summary}")
            elif rating <= 2:
                disliked_movies.append(f"امتیاز {rating} ستاره (عدم علاقه) به: {movie_summary}")
        except ValueError:
            pass 
            
    taste_profile = ""
    if liked_movies:
        taste_profile += "✅ کاربر به شدت به این سبک‌ها علاقه دارد:\n" + "\n".join(liked_movies) + "\n"
    if disliked_movies:
        taste_profile += "❌ کاربر از این سبک‌ها متنفر است (پیشنهاد نده):\n" + "\n".join(disliked_movies) + "\n"
        
    return taste_profile if taste_profile else "اطلاعات امتیازدهی کافی نیست."