import streamlit as st
from openai import OpenAI
from datetime import datetime
from fpdf import FPDF
import chromadb
from chromadb.utils import embedding_functions

# وارد کردن تنظیمات از فایل کانفیگ
import config

from database import (
    init_db, save_message, load_messages, get_user_sessions, 
    delete_session, update_feedback, save_user_profile, 
    get_user_profile, get_all_user_messages
)

# --- ۱. راه‌اندازی دیتابیس ---
init_db()

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

# --- ۴. تابع پروفایل‌سازی پنهان (درخواست استاد برای Cold Start) ---
def background_profile_update(username, client, gen_model_name):
    history = get_all_user_messages(username)
    msg_count = len(history)
    # آپدیت در پیام‌های ۲، ۵، ۱۰، ۲۰، ۴۰ (کاهش فرکانس به مرور زمان)
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
            pass # در بک‌اند ارور نمایش داده نمی‌شود تا کاربر متوجه نشود

# --- ۵. تنظیمات رابط کاربری ---
st.set_page_config(page_title="دستیار فیلم هوشمند", page_icon="🎬", layout="wide")
st.title("🎬 دستیار فیلم هوشمند")

# --- ۶. منوی کناری: حساب کاربری ---
st.sidebar.title("👤 حساب کاربری")
username = st.sidebar.text_input("نام کاربری:", value="guest", key="user_input")

if "last_user" not in st.session_state or st.session_state.last_user != username:
    st.session_state.last_user = username
    st.session_state.current_session = None
    st.session_state.messages = []
st.sidebar.divider()

# --- ۷. انتخاب حالت پردازش (ایده Fast/Pro/Ultra) ---
st.sidebar.title("🚀 قدرت پردازش سیستم")
selected_mode_name = st.sidebar.radio(
    "حالت پردازش را انتخاب کنید:", 
    list(config.PROCESSING_MODES.keys()),
    index=1 # پیش‌فرض روی حالت Pro
)
mode_config = config.PROCESSING_MODES[selected_mode_name]
st.sidebar.caption(mode_config["description"])
st.sidebar.divider()

# --- ۸. تنظیمات پیشرفته (پنهان در Expander) ---
with st.sidebar.expander("⚙️ تنظیمات پیشرفته مدل‌ها"):
    st.subheader("مدل پیشنهاددهنده")
    gen_model_type = st.radio("منبع مدل تولید:", ["لوکال (LM Studio)", "OpenAI API"], key="gen_radio")
    gen_temp = st.slider("خلاقیت:", 0.0, 1.0, config.GEN_DEFAULT_TEMP, 0.1, key="gen_temp")
    
    if gen_model_type == "لوکال (LM Studio)":
        gen_base_url = st.text_input("آدرس سرور:", value=config.GEN_DEFAULT_URL, key="gen_url")
        gen_api_key = config.GEN_DEFAULT_API_KEY
        gen_model_name = st.text_input("نام مدل:", value=config.GEN_DEFAULT_MODEL, key="gen_mname_loc")
    else:
        gen_api_key = st.text_input("API Key:", type="password", key="gen_key")
        gen_model_name = st.text_input("نام مدل API:", value="gpt-3.5-turbo", key="gen_mname_api")
        gen_base_url = "https://api.gapgpt.app/v1"
    
    client_gen = OpenAI(base_url=gen_base_url, api_key=gen_api_key) if gen_api_key else None

    st.divider()
    st.subheader("مدل منتقد")
    use_separate_critic = st.checkbox("استفاده از مدل مجزا برای منتقد", value=False)
    if use_separate_critic:
        cri_model_type = st.radio("منبع مدل منتقد:", ["OpenAI API", "لوکال (LM Studio)"], key="cri_radio")
        if cri_model_type == "لوکال (LM Studio)":
            cri_base_url = st.text_input("آدرس سرور منتقد:", value=config.CRI_DEFAULT_URL, key="cri_url")
            cri_api_key = config.CRI_DEFAULT_API_KEY
            cri_model_name = st.text_input("نام مدل منتقد:", value=config.CRI_DEFAULT_MODEL, key="cri_mname_loc")
        else:
            cri_api_key = st.text_input("API Key منتقد:", type="password", key="cri_key")
            cri_model_name = st.text_input("نام مدل API منتقد:", value="gpt-4o-mini", key="cri_mname_api")
            cri_base_url = "https://api.gapgpt.app/v1"
        
        client_critic = OpenAI(base_url=cri_base_url, api_key=cri_api_key) if cri_api_key else None
    else:
        client_critic = client_gen
        cri_model_name = gen_model_name

st.sidebar.divider()

# --- ۹. مدیریت تاریخچه چت ---
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

# --- ۱۰. نمایش پیام‌های قبلی ---
if not st.session_state.get("messages") or st.session_state.current_session:
    st.session_state.messages = load_messages(st.session_state.current_session)

for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# ==========================================
# 🧠 ۱۱. هسته پردازش پنهان چند-عامله (Multi-Agent Logic)
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
        if enable_critic and not client_critic:
            st.error("لطفا در تنظیمات پیشرفته، منبع مدل منتقد را تکمیل کنید.")
        else:
            with st.chat_message("assistant"):
                # استفاده از اسپینر ساده به جای وضعیت باز شونده (طبق نظر استاد)
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
                        
                        feedback_section = f"⚠️ ارور دور قبل که باید حتما اصلاح کنی:\n{critic_feedback}\n" if enable_critic and attempt > 1 else ""

                        GEN_PROMPT = f"""
                        تو یک هوش مصنوعی فوق‌حرفه‌ای و بسیار سخت‌گیر در معرفی فیلم هستی.
                        سلیقه کاربر: [{user_style}]
                        
                        <local_database>
                        {rag_context}
                        </local_database>

                        <critic_feedback>
                        {critic_feedback}
                        </critic_feedback>

                        <rules>
                        ۱. مسیریابی هیبریدی: اطلاعات داخل <local_database> فقط فیلم‌های ایرانی هستند. اگر کاربر فیلم خارجی خواست، این دیتابیس را نادیده بگیر و از دانش خودت فیلم جهانی معرفی کن. اگر فیلم ایرانی خواست، حتماً از دیتابیس استفاده کن.
                        ۲. فقط معرفی فیلم: اگر کاربر سوال بی‌ربط پرسید، بگو: "من فقط یک دستیار معرفی فیلم هستم."
                        ۳. زبان اجباری: تمام خروجی باید ۱۰۰٪ فارسی باشد.
                        ۴. تعداد مجاز: دقیقا تعداد درخواستی را معرفی کن (پیش‌فرض ۳). سقف مطلق ۶ فیلم است.
                        ۵. بدون حاشیه: هیچ مقدمه‌ای ننویس. مستقیم لیست را چاپ کن.
                        </rules>

                        <format>
                        🎬 **[نام فیلم به فارسی] ([نام انگلیسی] - [سال])** | ⭐ امتیاز: [امتیاز]
                        🎭 **ژانر:** [ژانر به فارسی]
                        💡 **چرا این فیلم؟** [توضیح کوتاه]
                        </format>
                        """

                        try:
                            gen_resp = client_gen.chat.completions.create(
                                model=gen_model_name,
                                messages=[{"role": "system", "content": GEN_PROMPT}, {"role": "user", "content": prompt}],
                                temperature=gen_temp
                            )
                            draft_response = gen_resp.choices[0].message.content
                            
                            if enable_critic:
                                CRITIC_PROMPT = f"""بررسی خروجی مدل دیگر. پیام کاربر: "{prompt}"
                                
                                <generated_text>
                                {draft_response}
                                </generated_text>

                                <evaluation_checklist>
                                ۱. آیا کلمه انگلیسی در متن هست؟
                                ۲. آیا تعداد فیلم‌ها بیشتر از ۶ عدد است؟
                                ۳. آیا تعداد با خواسته کاربر یکی است؟
                                ۴. آیا از ایموجی‌های فرمت استفاده شده است؟
                                </evaluation_checklist>

                                اگر بدون نقص بود بنویس: APPROVED
                                اگر اشتباه بود بنویس: ERROR: [دلیل و دستور اصلاح]
                                """
                                
                                cri_resp = client_critic.chat.completions.create(
                                    model=cri_model_name,
                                    messages=[{"role": "user", "content": CRITIC_PROMPT}],
                                    temperature=0.0
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
                
                # چاپ مستقیم خروجی نهایی
                st.markdown(final_response)
                
                # ذخیره در دیتابیس
                b_id = save_message(st.session_state.current_session, username, "assistant", final_response)
                st.session_state.messages.append({"id": b_id, "role": "assistant", "content": final_response, "feedback": None})
                
                # فراخوانی تابع آپدیت سلیقه در بک‌اند
                background_profile_update(username, client_gen, gen_model_name)
    else:
        st.error("لطفا در منوی تنظیمات پیشرفته، اتصال به مدل را پیکربندی کنید.")