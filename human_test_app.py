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

# --- دور زدن فیلترشکن در سطح سیستم‌عامل ---
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

import config
from database import init_db, get_golden_examples, save_golden_example

# تنظیمات صفحه
st.set_page_config(page_title="آزمایشگاه ارزیابی انسانی", layout="wide", page_icon="⚖️")

# فایل ذخیره‌سازی نتایج
CSV_FILE = "human_evaluation_results.csv"

# --- ۱. راه‌اندازی دیتابیس ---
init_db()

# --- ۲. تابع ارتباط مستقیم (Requests) ---
# --- ۲. تابع ارتباط با API (نسخه جدید با کتابخانه رسمی OpenAI) ---
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

# --- ۳. توابع RAG ---
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

# ==========================================
# 🧠 شبیه‌سازهای سیستم A و B
# ==========================================
def get_baseline_response(persona, query):
    # مدل خام: بدون RAG، بدون حافظه، فقط یک پرامپت ساده و بدون ناظر
    system_prompt = "تو یک دستیار پیشنهاد فیلم هستی. بر اساس سلیقه کاربر به او فیلم پیشنهاد بده."
    user_msg = f"سلیقه من: {persona}\n\nدرخواست من: {query}"
    try:
        ans = call_local_model(config.GEN_BASE_URL, config.GEN_API_KEY, config.GEN_MODEL_NAME, [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}], 0.7)
        return ans, "مدل خام ناظر ندارد."
    except Exception as e: return f"❌ خطا: {e}", ""

def get_proposed_response(persona, query):
    # مدل پیشنهادی ما: RAG + حافظه طلایی + ناظر فعال (Critic)
    try:
        # ۱. خواندن حافظه
        golden_examples_text = get_golden_examples(limit=2)
        
        # ۲. ترکیب هوشمند سلیقه و درخواست برای RAG
        rag_query = f"سلیقه: {persona} درخواست: {query}"
        rag_context = search_iranian_movies(rag_query, n_results=5)
        
        max_retries = 3 # حداکثر ۳ بار تلاش در صورت توهم
        attempt = 0
        approved = False
        final_response = ""
        draft_response = ""
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
            
            # تولید پاسخ اولیه
            draft_response = call_local_model(config.GEN_BASE_URL, config.GEN_API_KEY, config.GEN_MODEL_NAME, [{"role": "system", "content": GEN_PROMPT}, {"role": "user", "content": query}], config.GEN_TEMP)
            
            # فراخوانی ناظر (Critic) برای بررسی توهم
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
                # ۳. سیستم پاداش و ثبت در حافظه (در صورت نمره بالای ۸)
                try:
                    score_part = critic_feedback.upper().split("SCORE:")[-1].strip()
                    score_digits = ''.join(filter(str.isdigit, score_part))
                    if score_digits:
                        score = int(score_digits)
                        if score >= 8:
                            save_golden_example(draft_response)
                except Exception: pass
            else:
                final_response = draft_response # در صورت عدم تایید نهایی، آخرین درفت را برمی‌گرداند
                
        full_critic_history = "\n\n---\n\n".join(all_critic_logs)
        return final_response, full_critic_history
    except Exception as e: return f"❌ خطا: {e}", f"خطا در ناظر: {e}"

# ==========================================
# مدیریت وضعیت (Session State)
# ==========================================
if 'phase' not in st.session_state: st.session_state.phase = 1 
if 'step' not in st.session_state: st.session_state.step = 'input'
for key in ['left_model', 'right_model', 'response_left', 'response_right', 'critic_left', 'critic_right', 'user_persona', 'user_name', 'user_job', 'current_query']:
    if key not in st.session_state: st.session_state[key] = ""

# ==========================================
# 🎨 رابط کاربری
# ==========================================
st.title("🎬 آزمایشگاه ارزیابی انسانی (A/B Blind Test)")

# --- نوار کناری ---
st.sidebar.header("👤 اطلاعات شرکت‌کننده")
st.session_state.user_name = st.sidebar.text_input("نام فرد (اختیاری):", value=st.session_state.user_name)
st.session_state.user_job = st.sidebar.text_input("شغل / رشته تحصیلی:", value=st.session_state.user_job)
st.sidebar.markdown("---")
st.sidebar.info(f"📍 شما در **مرحله {st.session_state.phase} از 2** هستید.")

# ================== مرحله ۱: دریافت ورودی ==================
if st.session_state.step == 'input':
    if st.session_state.phase == 1:
        st.markdown("### 📝 تست اول: پرامپت ثابت (مقایسه استاندارد)")
        user_persona = st.text_area("سلیقه فیلم دیدن کاربر، ژانرهای مورد علاقه و خط قرمزها چیست؟", height=120, placeholder="مثال: من عاشق فیلم‌های طنز هستم...")
        query = "۳ فیلم ایرانی و ۲ فیلم خارجی به من پیشنهاد بده."
        st.info(f"📌 درخواست ثابت: **{query}**")
    else:
        st.markdown("### ✍️ تست دوم: پرامپت دلخواه کاربر")
        st.success(f"سلیقه ثبت شده: {st.session_state.user_persona}")
        user_persona = st.session_state.user_persona
        query = st.text_input("حالا کاربر هر درخواستی دارد اینجا بنویسد:", placeholder="مثال: یه فیلم کمدی شبیه فسیل بهم معرفی کن...")

    if st.button("🚀 شروع پردازش همزمان", type="primary"):
        if st.session_state.phase == 1 and not user_persona:
            st.warning("لطفاً سلیقه کاربر را وارد کنید.")
        elif st.session_state.phase == 2 and not query:
            st.warning("لطفاً درخواست کاربر را وارد کنید.")
        else:
            # اطلاع‌رسانی بابت زمان‌بر بودن روشن شدن ناظر
            with st.spinner("🤖 ربات‌ها و ناظر در حال پردازش و تصحیح هستند... (چون ناظر فعال است ممکن است ۱ تا ۲ دقیقه طول بکشد)"):
                
                # دریافت خروجی‌ها (متن پاسخ + گزارش ناظر)
                ans_base, crit_base = get_baseline_response(user_persona, query)
                ans_prop, crit_prop = get_proposed_response(user_persona, query)
                
                # جابجایی رندوم مدل‌ها به همراه لاگ‌های ناظر
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
    
    if st.button("✅ ثبت ارزیابی این مرحله"):
        if not reason:
            st.warning("لطفاً علت انتخاب را بنویسید.")
        else:
            # دیکد کردن نمرات، متن‌ها و گزارش ناظر
            if st.session_state.left_model == "Baseline":
                score_baseline = score_left
                score_proposed = score_right
                text_baseline = st.session_state.response_left
                text_proposed = st.session_state.response_right
                critic_log = st.session_state.critic_right
            else:
                score_baseline = score_right
                score_proposed = score_left
                text_baseline = st.session_state.response_right
                text_proposed = st.session_state.response_left
                critic_log = st.session_state.critic_left
                
            query_type = "Fixed" if st.session_state.phase == 1 else "Custom"
            
            # ذخیره دیتا در فایل CSV (با اضافه شدن فیلد منتقد)
            new_data = {
                "Name": st.session_state.user_name if st.session_state.user_name else "Anonymous",
                "Job": st.session_state.user_job,
                "Query_Type": query_type,
                "Query_Text": st.session_state.current_query,
                "Persona": st.session_state.user_persona,
                "Response_Baseline": text_baseline,
                "Response_Proposed": text_proposed,
                "Critic_Feedback": critic_log,      # 👈 مستندات ناظر ذخیره شد
                "Preferred_Side": pref,
                "Score_Baseline": score_baseline,
                "Score_Proposed": score_proposed,
                "Reason": reason
            }
            
            df_new = pd.DataFrame([new_data])
            
            # ذخیره ایمن در فایل CSV
            if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
                try:
                    df_existing = pd.read_csv(CSV_FILE)
                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                    df_combined.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
                except pd.errors.EmptyDataError:
                    df_new.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
            else:
                df_new.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
                
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
    
    st.markdown(f"دیتا در فایل `{CSV_FILE}` با موفقیت ذخیره شد.")
    
    if st.session_state.phase == 1:
        st.info("حالا باید مرحله دوم را با پرامپت دلخواه کاربر انجام دهید.")
        if st.button("➡️ ادامه به تست دوم (پرامپت دلخواه)"):
            st.session_state.phase = 2
            st.session_state.step = 'input'
            st.rerun()
    else:
        st.balloons()
        st.success("تست این شخص به طور کامل (هر دو مرحله) تمام شد!")
        if st.button("🔄 پایان و ثبت نفر جدید"):
            # پاک کردن حافظه موقت برای نفر بعدی
            for key in ['step', 'left_model', 'right_model', 'response_left', 'response_right', 'critic_left', 'critic_right', 'user_persona', 'current_query']:
                del st.session_state[key]
            st.session_state.phase = 1
            st.rerun()