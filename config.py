import os

# ==========================================
# 🗄️ تنظیمات دیتابیس‌ها (Database Configs)
# ==========================================
SQLITE_DB_PATH = "movies_app.db"
CHROMA_DB_DIR = "./chroma_db"
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# ==========================================
# 🤖 تنظیمات پیش‌فرض مدل‌ها (LLM Defaults)
# ==========================================
# تنظیمات عامل پیشنهاددهنده (Generator)
GEN_DEFAULT_URL = "http://localhost:8087/v1"
GEN_DEFAULT_API_KEY = "lm-studio"
GEN_DEFAULT_MODEL = "gemma-3-12b-it-qat"
GEN_DEFAULT_TEMP = 0.7

# تنظیمات عامل منتقد (Critic)
CRI_DEFAULT_URL = "http://localhost:8087/v1"
CRI_DEFAULT_API_KEY = "lm-studio"
CRI_DEFAULT_MODEL = "gemma-3-12b-it-qat"
CRI_DEFAULT_TEMP = 0.0

# ==========================================
# ⚙️ تنظیمات پردازش و رابط کاربری (Processing Modes)
# ==========================================
# پیاده‌سازی ایده استاد برای مخفی کردن منتقد و ایجاد ۳ سطح کاربری
PROCESSING_MODES = {
    "⚡ Fast (سریع)": {
        "description": "فقط تولید اولیه (بدون ارزیابی منتقد)",
        "use_critic": False,
        "max_retries": 1
    },
    "🧠 Pro (حرفه‌ای)": {
        "description": "تولید + ۱ دور بازبینی دقیق توسط منتقد",
        "use_critic": True,
        "max_retries": 2
    },
    "🔥 Ultra (فوق‌هوشمند)": {
        "description": "تولید + تا ۳ دور بحث و اصلاح خودکار برای تضمین کیفیت",
        "use_critic": True,
        "max_retries": 4
    }
}

# ==========================================
# 👤 تنظیمات پروفایل‌سازی پنهان (Implicit Profiling)
# ==========================================
# سلیقه کاربر هر چند پیام یک‌بار در بک‌اند آپدیت شود؟
PROFILE_UPDATE_FREQUENCY_INITIAL = 5  # برای کاربران جدید (سریع‌تر)
PROFILE_UPDATE_FREQUENCY_MATURE = 15  # برای کاربران قدیمی (دیرتر)