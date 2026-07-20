__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from openai import OpenAI
import streamlit as st
import pandas as pd
import random
import os
import requests
import chromadb
from chromadb.utils import embedding_functions

import config
from database import init_db, get_golden_examples, save_golden_example

# تنظیمات صفحه
st.set_page_config(page_title="آزمایشگاه ارزیابی انسانی", layout="wide", page_icon="⚖️")

# نام فایل‌های ذخیره‌سازی
CSV_FILE = "human_evaluation_results.csv"
DB_FILE = "movies_app.db"  # اگر نام دیتابیس شما در database.py چیز دیگری است، اینجا تغییر دهید

# --- ۱. راه‌اندازی دیتابیس ---
init_db()

# --- ۲. تابع ارتباط با API ---
def call_local_model(base_url, api_key, model_name, messages, temperature):
    try:
        client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"API Error: {str(e)}")

# --- ۳. ارسال نوتیفیکیشن و فایل به تلگرام ---
def send_telegram_notification(data_dict, csv_path, db_path):
    try:
        token = st.secrets.get("TELEGRAM_TOKEN")
        chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
        
        if token and chat_id:
            # الف) ارسال پیام متنی
            msg = f"""✅ <b>یک تست جدید با موفقیت ثبت شد!</b>
👤 <b>نام:</b> {data_dict.get('Name', '-')}
💼 <b>شغل:</b> {data_dict.get('Job', '-')}
🏙 <b>شهر محل زندگی:</b> {data_dict.get('City', '-')}
📝 <b>نوع تست:</b> {data_dict.get('Query_Type', '-')}
🎭 <b>سلیقه:</b> {data_dict.get('Persona', '-')}
❓ <b>درخواست:</b> {data_dict.get('Query_Text', '-')}

🏆 <b>مدل پیروز:</b> {data_dict.get('Preferred_Side', '-')}
⭐️ <b>نمره مدل خام:</b> {data_dict.get('Score_Baseline', '-')}
🌟 <b>نمره مدل پیشنهادی:</b> {data_dict.get('Score_Proposed', '-')}

💡 <b>دلیل کاربر:</b> 
{data_dict.get('Reason', '-')}"""

            url_msg = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url_msg, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"})
            
            # ب) ارسال فایل اکسل (نتایج)
            url_doc = f"https://api.telegram.org/bot{token}/sendDocument"
            if os.path.exists(csv_path):
                with open(csv_path, 'rb') as f:
                    requests.post(url_doc, data={"chat_id": chat_id}, files={"document": f})
                    
            # ج) ارسال فایل دیتابیس (حافظه طلایی)
            if os.path.exists(db_path):
                with open(db_path, 'rb') as f:
                    requests.post(url_doc, data={"chat_id": chat_id}, files={"document": f})
    except Exception as e:
        pass # جلوگیری از کراش سایت در صورت فیلتر بودن یا قطعی تلگرام

# --- ۴. توابع RAG و شبیه‌سازها (مثل قبل) ---
@st.cache_resource
def load_vector_db():
    try:
        client = chromadb.PersistentClient(path=config.CHROMA_DB_DIR)
        emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=config.EMBEDDING_MODEL_NAME)
        return client.get_collection(name="iranian_movies", embedding_function=emb_fn)
    except: return None

def search_iranian_movies(query, n_results=5):
    collection = load_vector_db()
    if not collection: return "دیتابیس آفلاین در دسترس نیست."
    results = collection.query(query_texts=[query], n_results=n_results)
    context = ""
    if results and 'documents' in results and len(results['documents'][0]) > 0:
        for i in range(len(results['documents'][0])):
            context += f"▪️ {results['documents'][0][i]} (امتیاز: {results['metadatas'][0][i]['score']})\n"
    return context

def get_baseline_response(persona, query):
    system_prompt = "تو یک دستیار پیشنهاد فیلم هستی. بر اساس سلیقه کاربر به او فیلم پیشنهاد بده."
    user_msg = f"سلیقه من: {persona}\n\nدرخواست من: {query}"
    try:
        ans = call_local_model(config.GEN_BASE_URL, config.GEN_API_KEY, config.GEN_MODEL_NAME, [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}], 0.7)
        return ans, "مدل خام ناظر ندارد."
    except Exception as e: return f"❌ خطا: {e}", ""

def get_proposed_response(persona, query):
    try:
        golden_examples_text = get_golden_examples(limit=2)
        rag_query = f"سلیقه: {persona} درخواست: {query}"
        rag_context = search_iranian_movies(rag_query, n_results=5)
        
        max_retries = 3
        attempt = 0
        approved = False
        final_response = ""
        critic_feedback = ""
        all_critic_logs = []

        while attempt < max_retries and not approved:
            attempt += 1
            feedback_str = f"<critic_feedback>\n{critic_feedback}\n</critic_feedback>" if attempt > 1 else ""
            
            GEN_PROMPT = config.GEN_PROMPT_TEMPLATE.format(
                user_style=persona, rating_history="کاربر جدید در تست انسانی", 
                golden_examples=golden_examples_text, rag_context=rag_context, 
                feedback_section=feedback_str
            )
            
            draft_response = call_local_model(config.GEN_BASE_URL, config.GEN_API_KEY, config.GEN_MODEL_NAME, [{"role": "system", "content": GEN_PROMPT}, {"role": "user", "content": query}], config.GEN_TEMP)
            
            CRITIC_PROMPT = config.CRITIC_PROMPT_TEMPLATE.format(
                user_prompt=f"سلیقه: {persona}\nدرخواست: {query}",
                draft_response=draft_response
            )
            
            cri_model = config.CRI_MODEL_NAME if config.USE_SEPARATE_CRITIC else config.GEN_MODEL_NAME
            cri_url = config.CRI_BASE_URL if config.USE_SEPARATE_CRITIC else config.GEN_BASE_URL
            cri_key = config.CRI_API_KEY if config.USE_SEPARATE_CRITIC else config.GEN_API_KEY
            
            critic_feedback = call_local_model(cri_url, cri_key, cri_model, [{"role": "user", "content": CRITIC_PROMPT}], config.CRI_TEMP)
            all_critic_logs.append(f"🔄 تلاش {attempt}:\n{critic_feedback}")
            
            if "APPROVED" in critic_feedback.upper():
                approved = True
                final_response = draft_response
                try:
                    score_part = critic_feedback.upper().split("SCORE:")[-1].strip()
                    score_digits = ''.join(filter(str.isdigit, score_part))
                    if score_digits and int(score_digits) >= 8:
                        save_golden_example(draft_response)
                except Exception: pass
            else:
                final_response = draft_response
                
        full_critic_history = "\n\n---\n\n".join(all_critic_logs)
        return final_response, full_critic_history
    except Exception as e: return f"❌ خطا: {e}", f"خطا در ناظر: {e}"

# ==========================================
# مدیریت وضعیت (Session State)
# ==========================================
# تغییر گام اولیه به صفحه ثبت‌نام (welcome)
if 'step' not in st.session_state: st.session_state.step = 'welcome' 
if 'phase' not in st.session_state: st.session_state.phase = 1 

for key in ['left_model', 'right_model', 'response_left', 'response_right', 'critic_left', 'critic_right', 'user_persona', 'current_query', 'user_name', 'user_job', 'user_city']:
    if key not in st.session_state: st.session_state[key] = ""

# ==========================================
# 🎨 رابط کاربری
# ==========================================
st.title("🎬 آزمایشگاه ارزیابی انسانی (A/B Blind Test)")

# نمایش پیام رضایت‌نامه به صورت دائمی در بالای تمام صفحات
st.info("⚖️ **رضایت‌نامه پژوهشی:** نتیجه این تست و اطلاعاتی که وارد می‌کنید، با رضایت شما به صورت عمومی (Public) در راستای اهداف پژوهشی و علمی قابل استفاده و انتشار است.")

# نوار کناری خلوت‌تر شده
st.sidebar.info(f"📍 شما در **مرحله {st.session_state.phase} از 2** هستید.")
st.sidebar.markdown("---")
st.sidebar.markdown("🛡️ **دسترسی پنل مخفی (فقط ادمین)**")
admin_password = st.sidebar.text_input("رمز عبور ادمین:", type="password")
CORRECT_PASSWORD = st.secrets.get("ADMIN_PASSWORD", None)
if admin_password:
    if CORRECT_PASSWORD is None:
        st.sidebar.error("⚠️ رمز در Secrets ست نشده است.")
    elif admin_password == CORRECT_PASSWORD:
        st.sidebar.success("✅ دسترسی تایید شد")
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, "rb") as file:
                st.sidebar.download_button("📥 دانلود اکسل", file, CSV_FILE, "text/csv")
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as db_file:
                st.sidebar.download_button("🧠 دانلود دیتابیس", db_file, DB_FILE, "application/octet-stream")
    else:
        st.sidebar.error("❌ رمز اشتباه است")

# ================== مرحله ۰: دریافت اطلاعات پایه (فقط یک‌بار) ==================
if st.session_state.step == 'welcome':
    st.markdown("### 👤 اطلاعات شرکت‌کننده")
    st.write("لطفاً پیش از شروع تست، فرم زیر را با دقت تکمیل کنید. پر کردن فیلدهای ستاره‌دار الزامی است.")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            name_input = st.text_input("نام و نام خانوادگی ٭", value=st.session_state.user_name)
        with col2:
            job_input = st.text_input("شغل / رشته تحصیلی ٭", value=st.session_state.user_job)
            
        city_input = st.text_input("شهر محل زندگی و کار ٭", value=st.session_state.user_city)
        
        if st.button("ورود به آزمایشگاه 🚀", type="primary", use_container_width=True):
            if not name_input.strip() or not job_input.strip() or not city_input.strip():
                st.error("⚠️ لطفاً تمام فیلدهای ستاره‌دار (٭) را پر کنید.")
            else:
                st.session_state.user_name = name_input
                st.session_state.user_job = job_input
                st.session_state.user_city = city_input
                st.session_state.step = 'input'
                st.rerun()

# ================== مرحله ۱: دریافت ورودی ==================
elif st.session_state.step == 'input':
    if st.session_state.phase == 1:
        st.markdown("### 📝 تست اول: پرامپت ثابت (مقایسه استاندارد)")
        user_persona = st.text_area("سلیقه فیلم دیدن کاربر، ژانرهای مورد علاقه و خط قرمزها چیست؟", height=120, placeholder="مثال: من عاشق فیلم‌های طنز هستم...")
        query = "۳ فیلم ایرانی و ۲ فیلم خارجی به من پیشنهاد بده."
        st.info(f"📌 درخواست ثابت: **{query}**")
    else:
        st.markdown("### ✍️ تست دوم: پرامپت دلخواه کاربر")
        st.success(f"سلیقه ثبت شده: {st.session_state.user_persona}")
        user_persona = st.session_state.user_persona
        query = st.text_input("حالا هر درخواستی دارید اینجا بنویسید:", placeholder="مثال: یه فیلم کمدی شبیه فسیل بهم معرفی کن...")

    if st.button("🚀 شروع پردازش همزمان", type="primary"):
        if st.session_state.phase == 1 and not user_persona:
            st.warning("لطفاً سلیقه کاربر را وارد کنید.")
        elif st.session_state.phase == 2 and not query:
            st.warning("لطفاً درخواست کاربر را وارد کنید.")
        else:
            with st.spinner("🤖 ربات‌ها و ناظر در حال پردازش و تصحیح هستند... (کمی صبور باشید)"):
                ans_base, crit_base = get_baseline_response(user_persona, query)
                ans_prop, crit_prop = get_proposed_response(user_persona, query)
                
                models = [("Baseline", ans_base, crit_base), ("Proposed", ans_prop, crit_prop)]
                random.shuffle(models)
                
                st.session_state.left_model, st.session_state.response_left, st.session_state.critic_left = models[0]
                st.session_state.right_model, st.session_state.response_right, st.session_state.critic_right = models[1]
                
                st.session_state.user_persona = user_persona
                st.session_state.current_query = query
                st.session_state.step = 'evaluate'
                st.rerun()

# ================== مرحله ۲: مقایسه و ارزیابی ==================
elif st.session_state.step == 'evaluate':
    st.markdown(f"### ⚖️ مقایسه خروجی‌ها (تست {st.session_state.phase})")
    st.write("دو سیستم هوش مصنوعی متفاوت، خروجی‌های زیر را تولید کرده‌اند. آن‌ها را بخوانید و قضاوت کنید.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🤖 پاسخ مدل سمت چپ")
        st.info(st.session_state.response_left)
    with col2:
        st.subheader("🤖 پاسخ مدل سمت راست")
        st.success(st.session_state.response_right)
        
    st.markdown("---")
    st.markdown("### 📊 فرم ارزیابی کاربر")
    pref = st.radio("۱. کاربر کدام پیشنهاد را ترجیح می‌دهد؟", ["مدل سمت راست", "مدل سمت چپ", "هیچکدام"])
    
    c1, c2 = st.columns(2)
    score_left = c1.slider("۲. نمره به مدل **سمت چپ** (1 تا 5):", 1, 5, 3)
    score_right = c2.slider("۳. نمره به مدل **سمت راست** (1 تا 5):", 1, 5, 3)
    reason = st.text_area("۴. علت انتخاب و نمره‌دهی چه بود؟")
    
    if st.button("✅ ثبت ارزیابی این مرحله", type="primary"):
        if not reason.strip():
            st.warning("لطفاً علت انتخاب را بنویسید.")
        else:
            if st.session_state.left_model == "Baseline":
                score_baseline, score_proposed = score_left, score_right
                text_baseline, text_proposed = st.session_state.response_left, st.session_state.response_right
                critic_log = st.session_state.critic_right
            else:
                score_baseline, score_proposed = score_right, score_left
                text_baseline, text_proposed = st.session_state.response_right, st.session_state.response_left
                critic_log = st.session_state.critic_left
                
            query_type = "Fixed" if st.session_state.phase == 1 else "Custom"
            
            new_data = {
                "Name": st.session_state.user_name,
                "Job": st.session_state.user_job,
                "City": st.session_state.user_city,
                "Query_Type": query_type,
                "Query_Text": st.session_state.current_query,
                "Persona": st.session_state.user_persona,
                "Response_Baseline": text_baseline,
                "Response_Proposed": text_proposed,
                "Critic_Feedback": critic_log,
                "Preferred_Side": pref,
                "Score_Baseline": score_baseline,
                "Score_Proposed": score_proposed,
                "Reason": reason
            }
            
            df_new = pd.DataFrame([new_data])
            
            if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
                try:
                    df_existing = pd.read_csv(CSV_FILE)
                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                    df_combined.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
                except pd.errors.EmptyDataError:
                    df_new.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
            else:
                df_new.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
                
            # ارسال نوتیفیکیشن و فایل‌ها به تلگرام
            send_telegram_notification(new_data, CSV_FILE, DB_FILE)
            
            st.session_state.step = 'reveal'
            st.rerun()

# ================== مرحله ۳: افشا و ادامه ==================
elif st.session_state.step == 'reveal':
    st.markdown("### 🎉 ارزیابی با موفقیت ثبت شد!")
    st.markdown("#### 🕵️‍♂️ هویت مدل‌ها فاش شد:")
    if st.session_state.left_model == "Proposed":
        st.success("✨ **مدل سمت چپ:** سیستم هوشمند ما (همراه با نظارت و حافظه) بود.")
        st.warning("⚙️ **مدل سمت راست:** سیستم خام و سنتی بود.")
    else:
        st.warning("⚙️ **مدل سمت چپ:** سیستم خام و سنتی بود.")
        st.success("✨ **مدل سمت راست:** سیستم هوشمند ما (همراه با نظارت و حافظه) بود.")
    
    st.markdown(f"دیتا در سیستم و سرورهای بک‌آپ ثبت شد.")
    
    if st.session_state.phase == 1:
        st.info("حالا باید مرحله دوم را با پرامپت دلخواه خود انجام دهید.")
        if st.button("➡️ ادامه به تست دوم (پرامپت دلخواه)"):
            st.session_state.phase = 2
            st.session_state.step = 'input'
            st.rerun()
    else:
        st.balloons()
        st.success("تست شما به طور کامل (هر دو مرحله) تمام شد! از همکاری شما سپاسگزاریم.")
        if st.button("🔄 پایان و شروع برای نفر جدید"):
            # پاک کردن حافظه موقت برای نفر بعدی
            for key in ['step', 'left_model', 'right_model', 'response_left', 'response_right', 'critic_left', 'critic_right', 'user_persona', 'current_query', 'user_name', 'user_job', 'user_city']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.phase = 1
            st.session_state.step = 'welcome' # بازگشت به صفحه ثبت اطلاعات
            st.rerun()