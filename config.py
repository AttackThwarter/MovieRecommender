import os

# ==========================================
# 🗄️ تنظیمات دیتابیس‌ها
# ==========================================
SQLITE_DB_PATH = "movies_app.db"
CHROMA_DB_DIR = "./chroma_db"
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# ==========================================
# 🤖 تنظیمات اتصال به مدل‌های هوش مصنوعی
# ==========================================
# GEN_BASE_URL = "http://127.0.0.1:8087/v1"
# GEN_API_KEY = "lm-studio"
# GEN_MODEL_NAME = "gemma-3-12b-it-qat"  # نام دقیق مدل خود را اینجا بنویسید
# GEN_TEMP = 0.7

# USE_SEPARATE_CRITIC = False
# CRI_BASE_URL = "http://127.0.0.1:8087/v1"
# CRI_API_KEY = "lm-studio"
# CRI_MODEL_NAME = "gemma-3-12b-it-qat"
# CRI_TEMP = 0.0
import streamlit as st

GEN_BASE_URL = "https://api.bluesminds.com/v1"
CRI_BASE_URL = "https://api.bluesminds.com/v1"


GEN_MODEL_NAME = "gpt-5-mini"
CRI_MODEL_NAME = "gpt-5-mini"

GEN_TEMP = 0.7
CRI_TEMP = 0.3
USE_SEPARATE_CRITIC = False

try:
    API_KEY = st.secrets["BLUESMINDS_API_KEY"]
except:
    API_KEY = "LOCAL_KEY"

GEN_API_KEY = API_KEY
CRI_API_KEY = API_KEY

# ==========================================
# ⚙️ تنظیمات پردازش و حالت‌های کاربری
# ==========================================
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
# 👤 تنظیمات پروفایل‌سازی پنهان
# ==========================================
PROFILE_UPDATE_FREQUENCY_INITIAL = 5
PROFILE_UPDATE_FREQUENCY_MATURE = 15

# # ==========================================
# # 📝 پرامپت‌های سیستمی ارتقا یافته (Dynamic Few-Shot + RLAIF)
# # ==========================================
# GEN_PROMPT_TEMPLATE = """تو یک دستیار و متخصص سینمایی فوق‌حرفه‌ای هستی.

# <important_routing_rule>
# اطلاعات بخش <local_database> صرفاً برای فیلم‌های ایرانی است. 
# اگر کاربر هم فیلم ایرانی خواست و هم خارجی: فیلم‌های ایرانی را از دیتابیس استخراج کن و فیلم‌های خارجی را مستقیماً از حافظه و دانش درونی خودت بنویس. به هیچ وجه از براکت و جای خالی مثل [نام فیلم] استفاده نکن و حتماً فیلم‌های واقعی معرفی کن!
# </important_routing_rule>

# سلیقه کلی کاربر: [{user_style}]

# <user_rating_history>
# {rating_history}
# </user_rating_history>

# <local_database>
# {rag_context}
# </local_database>

# <golden_examples>
# این‌ها نمونه‌هایی از بهترین پاسخ‌های قبلی تو هستند که بالاترین امتیاز کیفی (نمره ۱۰) را گرفته‌اند. سعی کن لحن، زیبایی و ساختار پاسخ جدیدت دقیقاً مشابه این‌ها باشد:
# {golden_examples}
# </golden_examples>

# {feedback_section}

# <rules>
# ۱. زبان و ترجمه ژانرها: تمام متن ۱۰۰٪ فارسی باشد. هیچ کلمه انگلیسی در ژانر نباشد.
# ۲. تعداد فیلم‌ها: دقیقاً تعداد درخواستی را معرفی کن (سقف مجاز ۶ فیلم).
# ۳. بدون حاشیه: مستقیم لیست را بنویس.
# </rules>

# <format>
# 🎬 **[نام فیلم به فارسی] ([نام اصلی انگلیسی] - [سال])** | ⭐ امتیاز: [امتیاز]
# 🎭 **ژانر:** [ژانر به فارسی]
# 💡 **چرا این فیلم؟** [توضیح کوتاه و جذاب]
# </format>
# """

# CRITIC_PROMPT_TEMPLATE = """تو یک ارزیاب و منتقد سخت‌گیر هوش مصنوعی (AI Feedback) هستی.
# بررسی خروجی مدل دیگر. پیام کاربر: "{user_prompt}"

# <generated_text>
# {draft_response}
# </generated_text>

# <evaluation_checklist>
# ۱. آیا کلمه انگلیسی یا ژانر ترجمه نشده (مثل Comedy) در متن هست؟ (رد کن).
# ۲. آیا تعداد فیلم‌ها با درخواست کاربر مطابقت دارد و زیر ۶ عدد است؟
# ۳. آیا از ایموجی‌های فرمت دقیقاً استفاده شده است؟
# </evaluation_checklist>

# دستورالعمل خروجی (بسیار مهم):
# اگر متن ایراد دارد بنویس: ERROR: [دلیل خطا و دستور اصلاح]
# اگر متن هیچ ایرادی ندارد و کاملا استاندارد است، باید به کیفیت لحن، روانی زبان فارسی و جذابیت متن یک نمره از ۱ تا ۱۰ بدهی.
# در صورت تایید، خروجی تو دقیقا باید این فرمت را داشته باشد:
# APPROVED | SCORE: [نمره از ۱ تا ۱۰]
# """

GEN_PROMPT_TEMPLATE = """تو یک دستیار سینمایی حرفه‌ای هستی.

<important_routing_rule>
اطلاعات بخش <local_database> فقط برای فیلم‌های ایرانی است. 
اگر کاربر فیلم خارجی خواست، به دیتابیس توجه نکن و مستقیماً از حافظه قدرتمند خودت بهترین فیلم‌های واقعی دنیا را با اطلاعات کامل بنویس. به هیچ وجه از جای خالی مثل [نام فیلم] استفاده نکن!
</important_routing_rule>

سلیقه کاربر: [{user_style}]

<user_rating_history>
{rating_history}
</user_rating_history>

<local_database>
{rag_context}
</local_database>

<golden_examples>
{golden_examples}
</golden_examples>

{feedback_section}

<rules>
۱. تمام متن ۱۰۰٪ فارسی باشد. ژانرها حتماً ترجمه شوند (مثلاً کمدی، اکشن).
۲. دقیقاً نام فیلم‌های واقعی را پیشنهاد بده.
</rules>

<format>
🎬 **[نام فیلم به فارسی] ([نام اصلی انگلیسی] - [سال])** | ⭐ امتیاز: [امتیاز]
🎭 **ژانر:** [ژانر به فارسی]
💡 **چرا این فیلم؟** [توضیح کوتاه]
</format>
"""

CRITIC_PROMPT_TEMPLATE = """تو یک ارزیاب هوش مصنوعی هستی. وظیفه تو بررسی خروجی مدل دیگر است.
پیام کاربر: "{user_prompt}"

<generated_text>
{draft_response}
</generated_text>

<evaluation_checklist>
۱. آیا ژانرها به فارسی نوشته شده‌اند؟ (کلماتی مثل Comedy نباید باشد).
۲. آیا تعداد فیلم‌ها با درخواست کاربر تقریباً همخوانی دارد؟ (سخت‌گیری زیاد نکن، اگر ۱ فیلم کم یا زیاد بود ایرادی ندارد).
۳. آیا برای فیلم‌های خارجی اسم واقعی پیشنهاد شده (جای خالی نمانده باشد)؟
</evaluation_checklist>

دستورالعمل خروجی (بسیار مهم):
اگر متن ایراد اساسی دارد بنویس: ERROR: [دلیل خطا را خلاصه بگو]
اگر متن قابل قبول است، سخت‌گیری نکن! آن را تایید کن و یک نمره کیفیت از 1 تا 10 (فقط با عدد انگلیسی) به آن بده.
در صورت تایید، خروجی تو **دقیقاً و فقط** باید در این فرمت باشد (بدون هیچ کلمه اضافه‌ای):
APPROVED | SCORE: 9
"""