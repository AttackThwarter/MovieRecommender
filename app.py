import streamlit as st
from openai import OpenAI
from datetime import datetime
from database import init_db, save_message, load_messages, get_user_sessions, delete_session, update_feedback

# ۱. راه‌اندازی دیتابیس (مطمئن شو فایل database.py در همین پوشه است)
init_db()

st.set_page_config(page_title="دستیار پیشنهاد فیلم", page_icon="🎬", layout="wide")
st.title("🎬 پیشنهاددهنده هوشمند فیلم")

# ۲. مدیریت حساب کاربری در سایدبار
st.sidebar.title("👤 حساب کاربری")
username = st.sidebar.text_input("نام کاربری:", value="guest", key="user_input")

if "last_user" not in st.session_state or st.session_state.last_user != username:
    st.session_state.last_user = username
    st.session_state.current_session = None
    st.session_state.messages = []

st.sidebar.divider()

# ۳. مدیریت نشست‌ها (Sessions)
st.sidebar.title("💬 مدیریت چت‌ها")
user_sessions = get_user_sessions(username)

if st.sidebar.button("➕ چت جدید", use_container_width=True):
    new_sid = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.current_session = new_sid
    st.session_state.messages = []
    save_message(new_sid, username, "system", "Session Started")
    st.rerun()

if not st.session_state.get("current_session") or (st.session_state.current_session not in user_sessions and not st.session_state.messages):
    if user_sessions:
        st.session_state.current_session = user_sessions[0]
    else:
        st.session_state.current_session = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if user_sessions:
    try:
        current_idx = user_sessions.index(st.session_state.current_session)
    except ValueError:
        current_idx = 0
    selected_session = st.sidebar.radio("تاریخچه چت‌ها:", user_sessions, index=current_idx)
    if selected_session != st.session_state.current_session:
        st.session_state.current_session = selected_session
        st.session_state.messages = load_messages(selected_session)
        st.rerun()

if st.sidebar.button("🗑️ پاک کردن این چت"):
    delete_session(st.session_state.current_session)
    st.session_state.current_session = None
    st.rerun()

st.sidebar.divider()

# ۴. تنظیمات هوش مصنوعی
st.sidebar.title("⚙️ تنظیمات مدل")
model_type = st.sidebar.radio("منبع مدل:", ["لوکال (LM Studio)", "OpenAI API"])
temp_value = st.sidebar.slider("خلاقیت (Temperature):", 0.0, 1.0, 0.7, 0.1)

if model_type == "لوکال (LM Studio)":
    base_url = st.sidebar.text_input("آدرس سرور لوکال:", value="http://localhost:1234/v1")
    api_key = "lm-studio"
    model_name = "local-model"
else:
    api_key = st.sidebar.text_input("API Key:", type="password")
    model_name = st.sidebar.text_input("Model Name:", value="gpt-3.5-turbo")
    base_url = "https://api.openai.com/v1"

client = None
if api_key:
    client = OpenAI(base_url=base_url, api_key=api_key)

# ۵. نمایش پیام‌ها
if not st.session_state.get("messages") or st.session_state.current_session:
    st.session_state.messages = load_messages(st.session_state.current_session)

for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("feedback") is not None:
                st.write("👍" if message["feedback"] == 1 else "👎")

# ۶. بخش اصلی: ارسال پیام با تزریق پرامپت طلایی
if prompt := st.chat_input("سلام! چه فیلمی پیشنهاد می‌دی؟"):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    u_id = save_message(st.session_state.current_session, username, "user", prompt)
    st.session_state.messages.append({"id": u_id, "role": "user", "content": prompt, "feedback": None})

    if client:
        with st.chat_message("assistant"):
            try:
                # --- مغز متفکر سیستم (The Golden Prompt) ---
                # این متن در هر بار ارسال پیام به مدل دیکته می‌شود تا قوانین فراموش نشوند
                FULL_SYSTEM_PROMPT = """
                تو یک منتقد سینما و متخصص پیشنهاد فیلم با دانش دایره‌المعارفی هستی.
                وظیفه تو این است که بر اساس سلیقه کاربر، بهترین فیلم‌ها را پیشنهاد دهی.

                قوانین حیاتی:
                ۱. فقط فیلم‌های واقعی و معتبر پیشنهاد بده. هرگز فیلم اختراع نکن (Anti-Hallucination).
                ۲. در هر پاسخ دقیقا ۳ فیلم پیشنهاد بده. نام فیلم‌ها را حتما به زبان انگلیسی بنویس.
                ۳. تنوع را رعایت کن: ترکیبی از شاهکارهای معروف و فیلم‌های مستقل یا کمتر دیده شده (Hidden Gems).
                ۴. پاسخ تو باید صمیمی، فارسی و دقیقا با فرمت زیر باشد (هیچ متن اضافه‌ای ننویس):

                خروجی تو حتما باید دقیقا با فرمت زیر باشد (بدون هیچ متن اضافه یا خط تیره اضافه):

                🎬 **[Movie Name]** ([Year])
                🎭 **ژانر:** [فارسی]
                💡 **چرا این فیلم؟** [توضیح جذاب در یک خط به فارسی]

                ---
                مثال برای الگوبرداری (Few-Shot Example):
                🎬 **The Prestige** (2006)
                🎭 **ژانر:** معمایی، درام
                💡 **چرا این فیلم؟** داستانی پیچیده و خیره‌کننده درباره رقابت دو شعبده‌باز که تا لحظه آخر شما را غافلگیر می‌کند.
                """

                # ساخت لیست پیام‌ها برای API (تزریق پرامپت در ابتدای لیست)
                messages_for_api = [{"role": "system", "content": FULL_SYSTEM_PROMPT}]
                for m in st.session_state.messages:
                    if m["role"] != "system": # پیام‌های سیستم قبلی دیتابیس را نادیده می‌گیریم تا با پرامپت جدید تداخل نکنند
                        messages_for_api.append({"role": m["role"], "content": m["content"]})

                stream = client.chat.completions.create(
                    model=model_name,
                    messages=messages_for_api,
                    temperature=temp_value,
                    stream=True 
                )
                bot_response = st.write_stream(stream)
                
                b_id = save_message(st.session_state.current_session, username, "assistant", bot_response)
                st.session_state.messages.append({"id": b_id, "role": "assistant", "content": bot_response, "feedback": None})
                st.rerun()
                
            except Exception as e:
                st.error(f"خطا در مدل: {e}")

# ۷. ثبت فیدبک
if len(st.session_state.messages) > 1 and st.session_state.messages[-1]["role"] == "assistant":
    last_msg = st.session_state.messages[-1]
    if last_msg.get("feedback") is None:
        feedback = st.feedback("thumbs", key=f"fb_{last_msg['id']}")
        if feedback is not None:
            update_feedback(last_msg["id"], feedback)
            st.session_state.messages[-1]["feedback"] = feedback
            st.toast("بازخورد شما در دیتابیس ذخیره شد.")