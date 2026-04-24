import streamlit as st
from openai import OpenAI
from datetime import datetime
from database import (
    init_db, save_message, load_messages, get_user_sessions, 
    delete_session, update_feedback, save_user_profile, 
    get_user_profile, get_all_user_messages
)

# ۱. راه‌اندازی دیتابیس
init_db()

st.set_page_config(page_title="دستیار پیشنهاد فیلم", page_icon="🎬", layout="wide")
st.title("🎬 پیشنهاددهنده هوشمند فیلم")

# ۲. مدیریت حساب کاربری
st.sidebar.title("👤 حساب کاربری")
username = st.sidebar.text_input("نام کاربری:", value="guest", key="user_input")

if "last_user" not in st.session_state or st.session_state.last_user != username:
    st.session_state.last_user = username
    st.session_state.current_session = None
    st.session_state.messages = []

st.sidebar.divider()

# ۳. تنظیمات مدل (آورده شد بالا تا برای دکمه تحلیل در دسترس باشد)
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

st.sidebar.divider()

# ۴. سیستم هوشمند پروفایل‌سازی (ویژگی جدید)
st.sidebar.title("🧠 هوش مصنوعی شخصی‌ساز")
user_style = get_user_profile(username)
st.sidebar.info(f"**سلیقه کشف‌شده شما:**\n\n{user_style}")

if st.sidebar.button("🔍 تحلیل رفتار و کشف سلیقه", use_container_width=True):
    if client:
        history = get_all_user_messages(username)
        if len(history) < 2:
            st.sidebar.warning("لطفاً اول چند پیام بدهید تا بتوانم سلیقه شما را کشف کنم.")
        else:
            with st.spinner("در حال تحلیل روانشناسانه سلیقه شما..."):
                try:
                    analysis_prompt = f"""
                    تو یک روانشناس سینما هستی. با توجه به پیام‌های زیر که کاربر نوشته است، سلیقه سینمایی او را در یک جمله کوتاه و جذاب به زبان فارسی خلاصه کن. 
                    فقط روی ژانرها و علاقه‌مندی‌ها تمرکز کن.
                    پیام‌های کاربر: {str(history)}
                    """
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": analysis_prompt}],
                        temperature=0.3
                    )
                    profile_summary = response.choices[0].message.content
                    save_user_profile(username, profile_summary)
                    st.sidebar.success("سلیقه شما کشف و ذخیره شد!")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"خطا در تحلیل: {e}")
    else:
        st.sidebar.warning("لطفا ابتدا مدل را متصل کنید.")

st.sidebar.divider()

# ۵. مدیریت چت‌ها (Sessions)
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

# ۶. نمایش چت
if not st.session_state.get("messages") or st.session_state.current_session:
    st.session_state.messages = load_messages(st.session_state.current_session)

for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("feedback") is not None:
                st.write("👍" if message["feedback"] == 1 else "👎")

# ۷. دریافت پیام و تزریق پرامپت شخصی‌سازی شده
if prompt := st.chat_input("سلام! چه فیلمی پیشنهاد می‌دی؟"):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    u_id = save_message(st.session_state.current_session, username, "user", prompt)
    st.session_state.messages.append({"id": u_id, "role": "user", "content": prompt, "feedback": None})

    if client:
        with st.chat_message("assistant"):
            try:
                # خواندن سلیقه لحظه‌ای کاربر از دیتابیس
                current_user_profile = get_user_profile(username)
                
                # پرامپت طلایی ترکیب شده با پروفایل کاربر
                FULL_SYSTEM_PROMPT = f"""
                تو یک متخصص پیشنهاد فیلم با دانش دایره‌المعارفی هستی.
                
                *** پروفایل سلیقه این کاربر ***
                {current_user_profile}
                *******************************
                
                وظیفه: با توجه به پروفایل سلیقه کاربر و درخواستی که الان داده، بهترین پیشنهادها را بده.
                قوانین حیاتی:
                ۱. فقط فیلم‌های واقعی پیشنهاد بده.
                ۲. دقیقا ۳ فیلم معرفی کن. نام فیلم‌ها حتما انگلیسی باشد.
                ۳. پاسخ تو باید صمیمی، فارسی و دقیقا با فرمت زیر باشد (هیچ متن اضافه‌ای ننویس):

                🎬 **[Movie Name]** ([Year])
                🎭 **ژانر:** [فارسی]
                💡 **چرا این فیلم؟** [در یک خط توضیح بده که چرا با توجه به سلیقه او این فیلم را انتخاب کردی]
                """

                messages_for_api = [{"role": "system", "content": FULL_SYSTEM_PROMPT}]
                for m in st.session_state.messages:
                    if m["role"] != "system":
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

# ۸. سیستم فیدبک
if len(st.session_state.messages) > 1 and st.session_state.messages[-1]["role"] == "assistant":
    last_msg = st.session_state.messages[-1]
    if last_msg.get("feedback") is None:
        feedback = st.feedback("thumbs", key=f"fb_{last_msg['id']}")
        if feedback is not None:
            update_feedback(last_msg["id"], feedback)
            st.session_state.messages[-1]["feedback"] = feedback
            st.toast("بازخورد شما در دیتابیس ذخیره شد.")