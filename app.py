import streamlit as st
from openai import OpenAI
from datetime import datetime
from fpdf import FPDF
import chromadb
from chromadb.utils import embedding_functions
import os

# --- دور زدن فیلترشکن برای ارتباط لوکال ---
os.environ["NO_PROXY"] = "127.0.0.1,localhost"

# وارد کردن تنظیمات از فایل کانفیگ
import config

from database import (
    init_db, save_message, load_messages, get_user_sessions, 
    delete_session, update_feedback, save_user_profile, 
    get_user_profile, get_all_user_messages
)

# --- ۱. راه‌اندازی دیتابیس و کلاینت‌ها ---
init_db()

client_gen = OpenAI(base_url=config.GEN_BASE_URL, api_key=config.GEN_API_KEY) if config.GEN_API_KEY else None

if config.USE_SEPARATE_CRITIC:
    client_critic = OpenAI(base_url=config.CRI_BASE_URL, api_key=config.CRI_API_KEY) if config.CRI_API_KEY else None
    cri_model_name = config.CRI_MODEL_NAME
else:
    client_critic = client_gen
    cri_model_name = config.GEN_MODEL_NAME

# --- ۲. توابع RAG ---
@st.cache_resource
def load_vector_db():
    try:
        client = chromadb.PersistentClient(path=config.CHROMA_DB_DIR)
        emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=config.EMBEDDING_MODEL_NAME
        )
        return client.get_collection(name="iranian_movies", embedding_function=emb_fn)
    except:
        return None

def search_iranian_movies(query, n_results=5):
    collection = load_vector_db()
    if not collection: return "دیتابیس آفلاین در دسترس نیست."
    results = collection.query(query_texts=[query], n_results=n_results)
    context = ""
    if results and 'documents' in results and len(results['documents'][0]) > 0:
        for i in range(len(results['documents'][0])):
            context += f"▪️ {results['documents'][0][i]} (امتیاز: {results['metadatas'][0][i]['score']})\n"
    return context

# --- ۳. توابع خروجی‌گیر ---
def create_txt_export(messages):
    text = "🎬 لیست پیشنهادی فیلم های من\n" + "="*30 + "\n\n"
    for m in messages:
        if m["role"] == "assistant":
            text += f"{m['content']}\n" + "-"*20 + "\n"
    return text

def create_pdf_export(messages):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.add_font('Vazir', '', 'Vazir.ttf')
        pdf.set_font('Vazir', size=12)
    except:
        pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt="لیست پیشنهادی فیلم", align='C')
    pdf.ln(10)
    for m in messages:
        if m["role"] == "assistant":
            clean_text = m['content'].replace("**", "")
            pdf.multi_cell(0, 10, txt=clean_text, align='R')
            pdf.ln(5)
            pdf.cell(0, 0, "-"*50, align='C')
            pdf.ln(5)
    return pdf.output()

# --- ۴. تابع پروفایل‌سازی پنهان ---
def background_profile_update(username, client, gen_model_name):
    history = get_all_user_messages(username)
    msg_count = len(history)
    if msg_count in [2, 5, 10, 20, 40] and client:
        try:
            analysis_prompt = f"با توجه به این پیام‌ها سلیقه سینمایی کاربر را در یک جمله کوتاه خلاصه کن: {str(history)}"
            response = client.chat.completions.create(
                model=gen_model_name, 
                messages=[{"role": "user", "content": analysis_prompt}], 
                temperature=0.3
            )
            save_user_profile(username, response.choices[0].message.content)
        except Exception:
            pass

# --- ۵. تنظیمات رابط کاربری ---
st.set_page_config(page_title="دستیار فیلم هوشمند", page_icon="🎬", layout="wide")
st.title("🎬 دستیار فیلم هوشمند")

# --- ۶. منوی کناری ---
st.sidebar.title("👤 حساب کاربری")
username = st.sidebar.text_input("نام کاربری:", value="guest", key="user_input")

if "last_user" not in st.session_state or st.session_state.last_user != username:
    st.session_state.last_user = username
    st.session_state.current_session = None
    st.session_state.messages = []
st.sidebar.divider()

st.sidebar.title("🚀 قدرت پردازش سیستم")
selected_mode_name = st.sidebar.radio(
    "حالت پردازش را انتخاب کنید:", 
    list(config.PROCESSING_MODES.keys()),
    index=1
)
mode_config = config.PROCESSING_MODES[selected_mode_name]
st.sidebar.caption(mode_config["description"])
st.sidebar.divider()

st.sidebar.title("💬 مدیریت چت‌ها")
user_sessions = get_user_sessions(username)

if not st.session_state.get("current_session"):
    st.session_state.current_session = user_sessions[0] if user_sessions else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if user_sessions:
    current_idx = user_sessions.index(st.session_state.current_session) if st.session_state.current_session in user_sessions else 0
    selected_session = st.sidebar.radio("تاریخچه چت‌ها:", user_sessions, index=current_idx)
    if selected_session != st.session_state.current_session:
        st.session_state.current_session = selected_session
        st.session_state.messages = load_messages(selected_session)
        st.rerun()

if st.sidebar.button("➕ چت جدید"):
    new_sid = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.current_session = new_sid
    st.session_state.messages = []
    save_message(new_sid, username, "system", "Session Started")
    st.rerun()

if st.sidebar.button("🗑️ پاک کردن این چت"):
    delete_session(st.session_state.current_session)
    st.session_state.current_session = None
    st.rerun()

# --- ۷. نمایش پیام‌های قبلی و سیستم فیدبک ---
if not st.session_state.get("messages") or st.session_state.current_session:
    st.session_state.messages = load_messages(st.session_state.current_session)

for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # رندر کردن دکمه‌های لایک و دیسلایک فقط برای پیام‌های هوش مصنوعی
            if message["role"] == "assistant":
                col1, col2, col3 = st.columns([1, 1, 8])
                with col1:
                    if st.button("👍", key=f"like_{message['id']}"):
                        update_feedback(message["id"], "like")
                        st.toast("عالی! سلیقه شما ثبت شد. 👍")
                with col2:
                    if st.button("👎", key=f"dislike_{message['id']}"):
                        update_feedback(message["id"], "dislike")
                        st.toast("ممنون! دفعه بعد فیلم‌های بهتری پیشنهاد می‌دم. 👎")

# ==========================================
# 🧠 ۸. هسته پردازش پنهان چند-عامله (Multi-Agent Logic)
# ==========================================
prompt = st.chat_input("چه فیلمی پیشنهاد می‌دی؟")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    u_id = save_message(st.session_state.current_session, username, "user", prompt)
    st.session_state.messages.append({"id": u_id, "role": "user", "content": prompt, "feedback": None})

    user_style = get_user_profile(username)

    if client_gen:
        enable_critic = mode_config["use_critic"]
        with st.chat_message("assistant"):
            with st.spinner(f"🤖 در حال بررسی و پردازش در بک‌اند ({selected_mode_name})..."):
                
                rag_context = search_iranian_movies(prompt, n_results=5)
                
                max_retries = mode_config["max_retries"]
                attempt = 0
                approved = False
                final_response = ""
                draft_response = "" 
                critic_feedback = ""

                while attempt < max_retries and not approved:
                    attempt += 1
                    
                    feedback_str = f"<critic_feedback>\n{critic_feedback}\n</critic_feedback>" if enable_critic and attempt > 1 else ""
                    GEN_PROMPT = config.GEN_PROMPT_TEMPLATE.format(
                        user_style=user_style,
                        rag_context=rag_context,
                        feedback_section=feedback_str
                    )

                    try:
                        gen_resp = client_gen.chat.completions.create(
                            model=config.GEN_MODEL_NAME,
                            messages=[{"role": "system", "content": GEN_PROMPT}, {"role": "user", "content": prompt}],
                            temperature=config.GEN_TEMP
                        )
                        draft_response = gen_resp.choices[0].message.content
                        
                        if enable_critic:
                            CRITIC_PROMPT = config.CRITIC_PROMPT_TEMPLATE.format(
                                user_prompt=prompt,
                                draft_response=draft_response
                            )
                            
                            cri_resp = client_critic.chat.completions.create(
                                model=cri_model_name,
                                messages=[{"role": "user", "content": CRITIC_PROMPT}],
                                temperature=config.CRI_TEMP
                            )
                            critic_feedback = cri_resp.choices[0].message.content
                            
                            if "APPROVED" in critic_feedback.upper():
                                approved = True
                                final_response = draft_response
                        else:
                            approved = True
                            final_response = draft_response
                            
                    except Exception as e:
                        final_response = f"❌ خطای ارتباط با مدل: {e}"
                        break 
                        
                if not approved and final_response == "":
                    final_response = draft_response if draft_response != "" else "متاسفانه ارتباط با مدل برقرار نشد."
            
            # --- اضافه کردن فیلد ظاهری (Badge) به انتهای پیام ---
            mode_badge = f"\n\n---\n*⚙️ تولید شده در حالت: **{selected_mode_name}***"
            final_response_with_badge = final_response + mode_badge
            
            # چاپ خروجی نهایی روی صفحه
            st.markdown(final_response_with_badge)
            
            # ذخیره متن همراه با بج در دیتابیس
            b_id = save_message(st.session_state.current_session, username, "assistant", final_response_with_badge)
            st.session_state.messages.append({"id": b_id, "role": "assistant", "content": final_response_with_badge, "feedback": None})
            
            # نمایش آنی دکمه‌ها برای پیام تازه تولید شده
            col1, col2, col3 = st.columns([1, 1, 8])
            with col1:
                if st.button("👍", key=f"like_{b_id}"):
                    update_feedback(b_id, "like")
                    st.toast("عالی! سلیقه شما ثبت شد. 👍")
            with col2:
                if st.button("👎", key=f"dislike_{b_id}"):
                    update_feedback(b_id, "dislike")
                    st.toast("ممنون! دفعه بعد فیلم‌های بهتری پیشنهاد می‌دم. 👎")
            
            background_profile_update(username, client_gen, config.GEN_MODEL_NAME)
    else:
        st.error("ارتباط با مدل برقرار نیست. لطفا فایل config.py را بررسی کنید.")