import streamlit as st
from openai import OpenAI
from datetime import datetime
from fpdf import FPDF # کتابخانه جدید برای PDF
from database import (
    init_db, save_message, load_messages, get_user_sessions, 
    delete_session, update_feedback, save_user_profile, 
    get_user_profile, get_all_user_messages
)

# ۱. راه‌اندازی دیتابیس
init_db()

# --- توابع کمکی برای خروجی گرفتن ---

def create_txt_export(messages):
    """تولید متن ساده برای خروجی TXT"""
    text = "🎬 لیست پیشنهادی فیلم های من\n"
    text += "="*30 + "\n\n"
    for m in messages:
        if m["role"] == "assistant":
            text += f"{m['content']}\n"
            text += "-"*20 + "\n"
    return text

def create_pdf_export(messages):
    """تولید فایل PDF با پشتیبانی از فارسی"""
    pdf = FPDF()
    pdf.add_page()
    
    # --- بارگذاری فونت فارسی (بسیار مهم) ---
    # شما باید فایل Vazir.ttf را در پوشه پروژه داشته باشید
    try:
        pdf.add_font('Vazir', '', 'Vazir.ttf')
        pdf.set_font('Vazir', size=12)
    except:
        # اگر فونت پیدا نشد، از فونت استاندارد استفاده می‌کند (که فارسی را خراب نشان می‌دهد)
        pdf.set_font("Arial", size=12)
    
    pdf.multi_cell(0, 10, txt="لیست پیشنهادی فیلم", align='C')
    pdf.ln(10)
    
    for m in messages:
        if m["role"] == "assistant":
            # تمیز کردن متن از ستاره‌های مارک‌داون برای PDF
            clean_text = m['content'].replace("**", "")
            pdf.multi_cell(0, 10, txt=clean_text, align='R')
            pdf.ln(5)
            pdf.cell(0, 0, "-"*50, align='C')
            pdf.ln(5)
            
    return pdf.output()

# --- تنظیمات صفحه ---
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

# ۳. تنظیمات مدل
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

# ۴. هوش مصنوعی شخصی‌ساز
st.sidebar.title("🧠 هوش مصنوعی شخصی‌ساز")
user_style = get_user_profile(username)
st.sidebar.info(f"**سلیقه شما:**\n\n{user_style}")

if st.sidebar.button("🔍 تحلیل رفتار و کشف سلیقه"):
    history = get_all_user_messages(username)
    if len(history) < 2:
        st.sidebar.warning("لطفاً اول چند پیام بدهید.")
    else:
        with st.spinner("در حال تحلیل..."):
            try:
                analysis_prompt = f"با توجه به این پیام‌ها سلیقه سینمایی کاربر را در یک جمله کوتاه خلاصه کن: {str(history)}"
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": analysis_prompt}],
                    temperature=0.3
                )
                profile_summary = response.choices[0].message.content
                save_user_profile(username, profile_summary)
                st.sidebar.success("سلیقه ذخیره شد!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"خطا: {e}")

st.sidebar.divider()

# ۵. مدیریت چت‌ها
st.sidebar.title("💬 مدیریت چت‌ها")
user_sessions = get_user_sessions(username)

if st.sidebar.button("➕ چت جدید"):
    new_sid = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.current_session = new_sid
    st.session_state.messages = []
    save_message(new_sid, username, "system", "Session Started")
    st.rerun()

if not st.session_state.get("current_session"):
    if user_sessions: st.session_state.current_session = user_sessions[0]
    else: st.session_state.current_session = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if user_sessions:
    selected_session = st.sidebar.radio("تاریخچه چت‌ها:", user_sessions, index=user_sessions.index(st.session_state.current_session) if st.session_state.current_session in user_sessions else 0)
    if selected_session != st.session_state.current_session:
        st.session_state.current_session = selected_session
        st.session_state.messages = load_messages(selected_session)
        st.rerun()

if st.sidebar.button("🗑️ پاک کردن این چت"):
    delete_session(st.session_state.current_session)
    st.session_state.current_session = None
    st.rerun()

st.sidebar.divider()

# --- ۶. بخش خروجی گرفتن (Export) ---
st.sidebar.title("📥 خروجی گرفتن")
if st.session_state.get("messages"):
    # دکمه دانلود TXT
    txt_data = create_txt_export(st.session_state.messages)
    st.sidebar.download_button(
        label="📄 دانلود به صورت TXT",
        data=txt_data,
        file_name=f"movies_{username}.txt",
        mime="text/plain",
        use_container_width=True
    )
    
    # دکمه دانلود PDF (نیاز به فونت در پوشه دارد)
    try:
        pdf_data = create_pdf_export(st.session_state.messages)
        st.sidebar.download_button(
            label="📕 دانلود به صورت PDF",
            data=pdf_data,
            file_name=f"movies_{username}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except:
        st.sidebar.error("خطا در تولید PDF (احتمالا فایل فونت Vazir.ttf وجود ندارد)")

# ۷. نمایش چت
if not st.session_state.get("messages") or st.session_state.current_session:
    st.session_state.messages = load_messages(st.session_state.current_session)

for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("feedback") is not None:
                st.write("👍" if message["feedback"] == 1 else "👎")

# ۸. دریافت پیام و تزریق پرامپت
if prompt := st.chat_input("چه فیلمی پیشنهاد می‌دی؟"):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    u_id = save_message(st.session_state.current_session, username, "user", prompt)
    st.session_state.messages.append({"id": u_id, "role": "user", "content": prompt, "feedback": None})

    if client:
        with st.chat_message("assistant"):
            try:
                current_user_profile = get_user_profile(username)
                FULL_SYSTEM_PROMPT = f"""
                تو یک متخصص فیلم هستی. سلیقه کاربر: [{current_user_profile}]
                قوانین: فقط فیلم واقعی، دقیقا ۳ عدد، نام انگلیسی، فرمت (🎬، 🎭، 💡).
                """
                messages_for_api = [{"role": "system", "content": FULL_SYSTEM_PROMPT}]
                for m in st.session_state.messages:
                    if m["role"] != "system":
                        messages_for_api.append({"role": m["role"], "content": m["content"]})

                stream = client.chat.completions.create(
                    model=model_name, messages=messages_for_api,
                    temperature=temp_value, stream=True 
                )
                bot_response = st.write_stream(stream)
                b_id = save_message(st.session_state.current_session, username, "assistant", bot_response)
                st.session_state.messages.append({"id": b_id, "role": "assistant", "content": bot_response, "feedback": None})
                st.rerun()
            except Exception as e:
                st.error(f"خطا: {e}")

# ۹. سیستم فیدبک
if len(st.session_state.messages) > 1 and st.session_state.messages[-1]["role"] == "assistant":
    last_msg = st.session_state.messages[-1]
    if last_msg.get("feedback") is None:
        feedback = st.feedback("thumbs", key=f"fb_{last_msg['id']}")
        if feedback is not None:
            update_feedback(last_msg["id"], feedback)
            st.session_state.messages[-1]["feedback"] = feedback
            st.toast("بازخورد ثبت شد.")