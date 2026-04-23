import streamlit as st
from openai import OpenAI
from database import init_db, save_message, load_messages

# ۱. راه‌اندازی اولیه دیتابیس (ساخت جدول در صورت عدم وجود)
init_db()

# ۲. تنظیمات اولیه ظاهر صفحه
st.set_page_config(page_title="دستیار پیشنهاد فیلم", page_icon="🎬", layout="wide")
st.title("🎬 پیشنهاددهنده هوشمند فیلم")

# ۳. منوی کناری (Sidebar)
st.sidebar.title("👤 حساب کاربری")
username = st.sidebar.text_input("نام کاربری خود را وارد کنید:", value="guest")

st.sidebar.divider()

st.sidebar.title("⚙️ تنظیمات مدل")
model_type = st.sidebar.radio("منبع مدل:", ["لوکال (LM Studio)", "OpenAI API"])
temp_value = st.sidebar.slider("میزان خلاقیت (Temperature):", 0.0, 1.0, 0.7, 0.1)

if model_type == "لوکال (LM Studio)":
    base_url = st.sidebar.text_input("آدرس سرور لوکال:", value="http://localhost:1234/v1")
    api_key = "lm-studio"
    model_name = "local-model"
    st.sidebar.caption("💡 مطمئن شوید سرور LM Studio در حالت Start است.")
else:
    api_key = st.sidebar.text_input("OpenAI API Key:", type="password")
    model_name = st.sidebar.text_input("Model Name:", value="gpt-3.5-turbo")
    base_url = "https://api.openai.com/v1"

# ۴. ساخت کلاینت برای ارتباط با مدل
client = None
if api_key:
    client = OpenAI(base_url=base_url, api_key=api_key)

# ۵. مدیریت حافظه و تاریخچه چت (اتصال به SQLite)
# اگر کاربر عوض شود، تاریخچه جدید را از دیتابیس می‌خوانیم
if "current_user" not in st.session_state or st.session_state.current_user != username:
    st.session_state.current_user = username
    # بارگذاری پیام‌ها از دیتابیس
    db_messages = load_messages(username)
    
    if db_messages:
        st.session_state.messages = db_messages
    else:
        # اگر کاربر سابقه‌ای ندارد، دستورالعمل سیستمی را تعریف کن
        system_prompt = """
        تو یک دستیار هوشمند، صمیمی و متخصص در زمینه پیشنهاد فیلم هستی.
        زبان اصلی تو برای ارتباط با کاربر "فارسی" است.

        قوانین تو:
        ۱. اگر کاربر درخواست نامشخصی داشت، از او بپرس چه ژانری دوست دارد یا چه حسی دارد.
        ۲. دقیقا ۳ فیلم واقعی و شناخته‌شده پیشنهاد بده.
        ۳. تنوع (بسیار مهم): ترکیبی از فیلم‌های مشهور و فیلم‌های کمتر دیده شده (Hidden Gems) را پیشنهاد بده.
        ۴. قانون ضد-توهم: هرگز فیلم اختراع نکن! نام فیلم‌ها حتما انگلیسی باشد.
        ۵. فرمت خروجی (بدون خط تیره):
        
        🎬 **[English Movie Name]** ([Year])
        🎭 **ژانر:** [ژانر به فارسی]
        💡 **چرا این فیلم؟** [توضیح کوتاه به فارسی]
        """
        st.session_state.messages = [{"role": "system", "content": system_prompt}]
        # ذخیره پیام سیستم برای کاربر جدید در دیتابیس
        save_message(username, "system", system_prompt)

# ۶. دکمه پاک کردن تاریخچه (اختیاری برای بهبود تجربه کاربری)
if st.sidebar.button("🗑️ پاک کردن تاریخچه چت"):
    import sqlite3
    conn = sqlite3.connect("movies_app.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    st.rerun()

# ۷. نمایش تاریخچه پیام‌ها روی صفحه
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# ۸. دریافت پیام جدید از کاربر و گرفتن پاسخ از هوش مصنوعی
if prompt := st.chat_input("سلام! چه فیلمی پیشنهاد می‌دی؟"):
    
    # نمایش و ذخیره پیام کاربر
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_message(username, "user", prompt)

    # فراخوانی مدل
    if client:
        with st.chat_message("assistant"):
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=st.session_state.messages,
                    temperature=temp_value
                )
                
                bot_response = response.choices[0].message.content
                st.markdown(bot_response)
                
                # ذخیره پاسخ مدل در حافظه و دیتابیس
                st.session_state.messages.append({"role": "assistant", "content": bot_response})
                save_message(username, "assistant", bot_response)
                
            except Exception as e:
                st.error(f"❌ خطا در مدل: {e}")
    else:
        st.warning("⚠️ کلید API یا تنظیمات لوکال وارد نشده است.")