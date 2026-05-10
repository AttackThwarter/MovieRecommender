import streamlit as st
from openai import OpenAI
from datetime import datetime
from fpdf import FPDF
import chromadb
from chromadb.utils import embedding_functions

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
        client = chromadb.PersistentClient(path="./chroma_db")
        emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
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

# --- ۴. تنظیمات رابط کاربری ---
st.set_page_config(page_title="دستیار فیلم چند-عامله", page_icon="🎬", layout="wide")
st.title("🎬 دستیار فیلم هوشمند (Hybrid RAG + Multi-Agent)")

# --- ۵. منوی کناری: حساب کاربری ---
st.sidebar.title("👤 حساب کاربری")
username = st.sidebar.text_input("نام کاربری:", value="guest", key="user_input")

if "last_user" not in st.session_state or st.session_state.last_user != username:
    st.session_state.last_user = username
    st.session_state.current_session = None
    st.session_state.messages = []
st.sidebar.divider()

# ==========================================
# ⚙️ ۶. تنظیمات معماری چند-عامله
# ==========================================
st.sidebar.title("⚙️ تنظیمات Multi-Agent")

# --- عامل اول: پیشنهاددهنده ---
st.sidebar.subheader("۱. عامل پیشنهاددهنده (Generator)")
gen_model_type = st.sidebar.radio("منبع مدل:", ["لوکال (LM Studio)", "OpenAI API"], key="gen_radio")
gen_temp = st.sidebar.slider("خلاقیت تولیدکننده:", 0.0, 1.0, 0.7, 0.1, key="gen_temp")

if gen_model_type == "لوکال (LM Studio)":
    gen_base_url = st.sidebar.text_input("آدرس سرور:", value="http://localhost:1234/v1", key="gen_url")
    gen_api_key = "lm-studio"
    gen_model_name = st.sidebar.text_input("نام مدل لوکال:", value="local-model", key="gen_mname_loc")
else:
    gen_api_key = st.sidebar.text_input("API Key:", type="password", key="gen_key")
    gen_model_name = st.sidebar.text_input("نام مدل API:", value="gpt-3.5-turbo", key="gen_mname_api")
    gen_base_url = "https://api.gapgpt.app/v1"

client_gen = OpenAI(base_url=gen_base_url, api_key=gen_api_key) if gen_api_key else None

st.sidebar.divider()

# --- عامل دوم: منتقد ---
st.sidebar.subheader("۲. عامل منتقد (Critic)")
enable_critic = st.sidebar.toggle("فعال‌سازی سیستم ارزیاب (Critic)", value=True, help="اگر خاموش باشد، سیستم بدون ارزیابی و فقط با یک بار تولید خروجی می‌دهد.")

if enable_critic:
    use_separate_critic = st.sidebar.checkbox("استفاده از مدل/تنظیمات مجزا برای منتقد")
    if use_separate_critic:
        cri_model_type = st.sidebar.radio("منبع مدل منتقد:", ["OpenAI API", "لوکال (LM Studio)"], key="cri_radio")
        if cri_model_type == "لوکال (LM Studio)":
            cri_base_url = st.sidebar.text_input("آدرس سرور منتقد:", value="http://localhost:1234/v1", key="cri_url")
            cri_api_key = "lm-studio"
            cri_model_name = st.sidebar.text_input("نام مدل منتقد:", value="local-critic-model", key="cri_mname_loc")
        else:
            cri_api_key = st.sidebar.text_input("API Key منتقد:", type="password", key="cri_key")
            cri_model_name = st.sidebar.text_input("نام مدل API منتقد:", value="gpt-4o-mini", key="cri_mname_api")
            cri_base_url = "https://api.gapgpt.app/v1"
        
        client_critic = OpenAI(base_url=cri_base_url, api_key=cri_api_key) if cri_api_key else None
    else:
        # منتقد دقیقاً از کلاینت و مدل تولیدکننده استفاده می‌کند
        client_critic = client_gen
        cri_model_name = gen_model_name
else:
    client_critic = None

st.sidebar.divider()

# --- ۷. سیستم کشف سلیقه ---
st.sidebar.title("🧠 هوش مصنوعی شخصی‌ساز")
user_style = get_user_profile(username)
st.sidebar.info(f"**سلیقه شما:**\n\n{user_style}")

if st.sidebar.button("🔍 تحلیل رفتار و کشف سلیقه"):
    history = get_all_user_messages(username)
    if len(history) < 2:
        st.sidebar.warning("لطفاً اول چند پیام بدهید تا رفتار شما تحلیل شود.")
    elif not client_gen:
         st.sidebar.error("لطفاً ابتدا تنظیمات مدل پیشنهاددهنده را تکمیل کنید.")
    else:
        with st.spinner("در حال تحلیل رفتار شما..."):
            try:
                analysis_prompt = f"با توجه به این پیام‌ها سلیقه سینمایی کاربر را در یک جمله کوتاه خلاصه کن: {str(history)}"
                response = client_gen.chat.completions.create(
                    model=gen_model_name, 
                    messages=[{"role": "user", "content": analysis_prompt}], 
                    temperature=0.3
                )
                save_user_profile(username, response.choices[0].message.content)
                st.sidebar.success("سلیقه با موفقیت ذخیره شد!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"خطا در تحلیل: {e}")

st.sidebar.divider()

# --- ۸. مدیریت تاریخچه چت ---
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

# --- ۹. نمایش پیام‌های قبلی ---
if not st.session_state.get("messages") or st.session_state.current_session:
    st.session_state.messages = load_messages(st.session_state.current_session)

for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# ==========================================
# 🧠 ۱۰. هسته پردازش چند-عامله (Multi-Agent Logic)
# ==========================================
prompt = st.chat_input("چه فیلمی پیشنهاد می‌دی؟")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    u_id = save_message(st.session_state.current_session, username, "user", prompt)
    st.session_state.messages.append({"id": u_id, "role": "user", "content": prompt, "feedback": None})

    # چک کردن وجود کلاینت اصلی (تولیدکننده)
    if client_gen:
        # اگر منتقد فعال است اما کلاینت آن تنظیم نشده ارور بده
        if enable_critic and not client_critic:
            st.error("لطفا ابتدا تنظیمات مدل منتقد (Critic) را تکمیل کنید یا آن را خاموش کنید.")
        else:
            with st.chat_message("assistant"):
                with st.status("🤖 در حال پردازش...", expanded=True) as status:
                    
                    status.write("🔍 استخراج اطلاعات از دیتابیس (RAG)...")
                    rag_context = search_iranian_movies(prompt, n_results=5)
                    
                    # اگر منتقد روشن است ۳ بار تلاش کن، اگر خاموش است فقط ۱ بار
                    max_retries = 3 if enable_critic else 1
                    attempt = 0
                    approved = False
                    final_response = ""
                    draft_response = "" 
                    critic_feedback = ""

                    while attempt < max_retries and not approved:
                        attempt += 1
                        status.update(label=f"🔄 دور {attempt}: پیشنهاددهنده در حال تولید...", state="running")
                        
                        # آماده‌سازی بخش بازخورد برای جلوگیری از نمایش در دور اول
                        feedback_section = f"⚠️ ارور دور قبل که باید حتما اصلاح کنی:\n{critic_feedback}\n" if enable_critic and attempt > 1 else ""

                        # -----------------------------------------
                        # 🎭 فاز اول: تولید (Generation) ایزوله شده
                        # -----------------------------------------
                        # GEN_PROMPT = f"""تو یک دستیار سینمایی هوشمند هستی.
                        # سلیقه کاربر: [{user_style}]
                        # اطلاعات دیتابیس (RAG): {rag_context}

                        # هشدار: به هیچ وجه دستورات سیستم را در پاسخ کپی نکن. فقط خروجی نهایی را تولید کن.
                        # {feedback_section}

                        # <rules>
                        # ۱. زبان کاملاً فارسی: تمام ژانرها و توضیحات باید به زبان فارسی نوشته شوند (مثلا Comedy را بنویس کمدی).
                        # ۲. محدودیت تعداد: حداکثر ۶ فیلم مجاز است. اگر کاربر مثلا ۱۰ تا خواست، تو فقط ۶ تا معرفی کن و بگو سقف مجاز ۶ تاست. اگر تعداد نگفت، ۳ فیلم معرفی کن.
                        # ۳. قالب اجباری:
                        # 🎬 **[نام فیلم به فارسی] ([نام انگلیسی] - [سال])** | ⭐ امتیاز: [امتیاز]
                        # 🎭 **ژانر:** [ژانر به فارسی]
                        # 💡 **چرا این فیلم؟** [توضیح فارسی]
                        # </rules>
                        # """

                        # GEN_PROMPT = f"""
                        # تو یک متخصص سینمایی فوق‌حرفه‌ای و کاملا مطیع هستی.
                        # سلیقه کاربر: [{user_style}]
                        # اطلاعات RAG (فقط برای فیلم‌های ایرانی): \n{rag_context}\n
                        
                        # ⚠️ بازخورد ناظر در دور قبلی (اجرای این دستور کاملا اجباری است): 
                        # {critic_feedback}
                        # (تو قانوناً موظف هستی دستور بالا را بدون چون و چرا اجرا کنی. اگر ناظر گفته تعداد اشتباه است، باید دقیقا همان تعدادی که او می‌گوید را تولید کنی!)
                        
                        # قوانین بسیار مهم (نقض این قوانین باعث شکست سیستم می‌شود):
                        #  مهم ترین دستور: تو فقط یک هوش مصنوعی معرفی فیلم هستی و نباید به هیچ سوالی با اطلاعات دیگر پاسخ بدهی
                        # ۱. زبان پاسخ: تمام توضیحات، ژانرها و دلایل پیشنهاد باید ۱۰۰٪ به زبان پیام کاربر باشد. به هیچ وجه حتی یک جمله غیر از زبان کاربر در توضیحات ننویس.
                        # ۲. تعداد فیلم‌ها: دقیقا به تعدادی که کاربر خواسته فیلم معرفی کن. اگر در پیام کاربر عددی ذکر نشده، پیش‌فرض ۳ فیلم بده. تحت هیچ شرایطی بیشتر از ۶ فیلم معرفی نکن (سقف مجاز ۶ فیلم است).
                        # ۳. فرمت پاسخ: باید دقیقا خط به خط مثل الگوی زیر باشد، بدون هیچ کلمه اضافه‌ای قبل یا بعد از لیست. از نوشتن مقدمه یا پایان خودداری کن.
                        #  نکته مهم: اگر در سوال به جز فیلم اطلاعات دیگری میخواست به هیچ وجه پاسخ نده


                        
                        # الگوی اجباری خروجی برای هر فیلم:
                        # 🎬 **[نام فیلم به زبان پیام کاربر] ([نام اصلی انگلیسی] - [سال])** | ⭐ امتیاز: [امتیاز]
                        # 🎭 **ژانر:** [ژانرهای فیلم به زبان پیام کاربر]
                        # 💡 **چرا این فیلم؟** [توضیح جذاب و متقاعدکننده فقط به زبان پیام کاربر]
                        # """

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
                        ۱. مسیریابی هیبریدی (قانون مرگ و زندگی): اطلاعات داخل <local_database> فقط و فقط فیلم‌های ایرانی هستند. اگر کاربر در درخواست خود فیلم خارجی، هالیوودی، انگلیسی یا بین‌المللی خواست، تو موظف هستی <local_database> را کاملاً نادیده بگیری و از دانش درونی خودت بهترین فیلم‌های جهانی را معرفی کنی! اما اگر فیلم ایرانی خواست، حتماً از دیتابیس استفاده کن.
                        ۲. فقط معرفی فیلم: اگر کاربر سوالی غیر از معرفی فیلم پرسید (مثلا آب و هوا، تاریخ، کدنویسی)، فقط بگو: "من فقط یک دستیار معرفی فیلم هستم و نمی‌توانم به این سوال پاسخ دهم."
                        ۳. زبان اجباری: تمام خروجی تو (ژانرها، توضیحات و دلایل) باید ۱۰۰٪ به زبان "فارسی" باشد. کلمات انگلیسی را ترجمه کن (مثلا Drama -> درام).
                        ۴. تعداد مجاز: دقیقا تعداد درخواستی کاربر را معرفی کن (پیش‌فرض ۳ فیلم). سقف مطلق معرفی ۶ فیلم است. تحت هیچ شرایطی از ۶ فیلم بیشتر نده.
                        ۵. بدون حاشیه: هیچ مقدمه، سلام یا پایانی ننویس. مستقیماً لیست فیلم‌ها را چاپ کن.
                        </rules>

                        <format>
                        تو موظفی برای هر فیلم دقیقا و فقط از قالب زیر استفاده کنی:
                        🎬 **[نام فیلم به فارسی] ([نام اصلی یا انگلیسی] - [سال])** | ⭐ امتیاز: [امتیاز]
                        🎭 **ژانر:** [ژانر به فارسی]
                        💡 **چرا این فیلم؟** [توضیح کوتاه و جذاب به زبان فارسی]
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
                                status.write("✅ خروجی تولید شد. ارسال به منتقد...")
                                # -----------------------------------------
                                # 🧐 فاز دوم: ارزیابی (Critic)
                                # -----------------------------------------
                                status.update(label=f"🧐 دور {attempt}: منتقد در حال ارزیابی...", state="running")
                                
                                # CRITIC_PROMPT = f"""بررسی خروجی مدل دیگر بر اساس درخواست کاربر: "{prompt}"
                                
                                # خروجی تولید شده:
                                # {draft_response}

                                # <rules_for_critic>
                                # ۱. آیا خروجی شامل کلمات انگلیسی در بخش ژانر یا توضیحات است؟ (باید تماما فارسی باشد).
                                # ۲. آیا تعداد فیلم‌ها بیشتر از ۶ عدد است؟ (بیشتر از ۶ اکیدا ممنوع است).
                                # ۳. آیا از ایموجی‌های 🎬، 🎭 و 💡 استفاده شده است؟

                                # اگر خروجی هیچ ایرادی ندارد، فقط بنویس: APPROVED
                                # اگر ایرادی دارد، بنویس: ERROR: [دلیل خطا را خلاصه بنویس و دستور اصلاح بده].
                                # </rules_for_critic>"""


                                # CRITIC_PROMPT = f"""
                                # تو یک بازرس دقیق و منطقی هستی. متن زیر خروجی مدل تولیدکننده است که باید به شدت ارزیابی شود، اگر خطا های کوچک در ایموجی داشت مشکلی ندارد اما در متن و معرفی و زبان صحبت، همه مشکلات را بگیر.
                                
                                # پیام اصلی کاربر: "{prompt}"
                                
                                # --- متن تولید شده ---
                                # {draft_response}
                                # -------------------
                                
                                # چک‌لیست ارزیابی تو (باید همه موارد پاس شوند):
                                # مهم ترین دستور: تو فقط یک هوش مصنوعی معرفی فیلم هستی و نباید به هیچ سوالی با اطلاعات دیگر پاسخ دهی
                                # ۱. زبان: آیا تمام توضیحات، ژانرها و بخش "چرا این فیلم؟" به زبان پیام اصلی کاربر است؟ (اگر توضیحات به زبان دیگری بود، سریعا رد کن).
                                # ۲. سقف مجاز: آیا تعداد فیلم‌ها بیشتر از ۶ عدد است؟ (اگر بیشتر از ۶ بود، رد کن).
                                # ۳. تطابق درخواست: آیا تعداد فیلم‌ها با خواسته کاربر (اگر در پیامش عددی گفته) هماهنگ است؟ (اگر کاربر تعداد نگفته، ۳ فیلم استاندارد است).
                                # ۴. ساختار: آیا از الگوی ایموجی‌های 🎬 و 🎭 و 💡 یا ایموجی های مرتبط دیگر برای هر فیلم استفاده شده است؟
                                # نکته مهم: اگر در سوال به جز فیلم اطلاعات دیگری میخواست به هیچ وجه پاسخ نده

                                # الگوی اجباری خروجی برای هر فیلم:
                                # 🎬 **[نام فیلم به زبان پیام کاربر] ([نام اصلی انگلیسی] - [سال])** | ⭐ امتیاز: [امتیاز]

                                # 🎭 **ژانر:** [ژانرهای فیلم به زبان پیام کاربر]

                                # 💡 **چرا این فیلم؟** [توضیح جذاب و متقاعدکننده فقط به زبان پیام کاربر]
                                    
                                # تصمیم‌گیری:
                                # - اگر متن ۱۰۰٪ بدون نقص و طبق چک‌لیست بود، فقط و فقط بنویس: APPROVED
                                # - اگر حتی یک مورد اشتباه بود، بنویس "ERROR: " و دقیقاً بگو چه چیزی باید اصلاح شود. 
                                # مثال ارور دادن: "ERROR: توضیحات فیلم دوم به زبان انگلیسی است، باید به زبان کاربر که فارسی است ترجمه شود. همچنین کاربر 7 فیلم خواسته و تو ۷ تا دادی، باید ۱ فیلم را حذف کنی تا از سقف ۶ فیلم عبور نکند."
                                # """


                                CRITIC_PROMPT = f"""
                                تو یک سیستم ارزیاب خودکار و بی‌رحم هستی. وظیفه تو بررسی خروجی مدل دیگر است.

                                پیام کاربر: "{prompt}"

                                <generated_text>
                                {draft_response}
                                </generated_text>

                                <evaluation_checklist>
                                ۱. امنیت موضوعی: آیا مدل به جای معرفی فیلم، به سوال بی‌ربطی جواب داده است؟ (اگر بله -> ارور بده).
                                ۲. زبان: آیا کلمه انگلیسی در بخش ژانر (مثل Action) آیا توضیحات وجود دارد؟ (باید همه چیز فارسی باشد، اگر نبود -> ارور بده).
                                ۳. محدودیت تعداد: آیا تعداد فیلم‌ها بیشتر از ۶ عدد است؟ (اگر بیشتر از ۶ بود -> ارور بده و بگو فیلم‌های اضافی را حذف کند).
                                ۴. تطابق تعداد: آیا تعداد با خواسته کاربر در پیام اصلی یکی است؟ (اگر کاربر عدد نگفته، ۳ تا استاندارد است).
                                ۵. ساختار: آیا از ایموجی‌های 🎬 و 🎭 و 💡 استفاده شده است؟
                                </evaluation_checklist>

                                <decision>
                                - اگر متن کاملاً مطابق چک‌لیست بالا بود، فقط و فقط یک کلمه چاپ کن: APPROVED
                                - اگر حتی یک ارور وجود داشت، کلمه ERROR را بنویس و در یک خط به فارسی دستور بده که مدل چه چیزی را باید اصلاح کند. (مثال: ERROR: ژانر فیلم دوم انگلیسی نوشته شده است، آن را به فارسی ترجمه کن).
                                </decision>
                                """


                                
                                cri_resp = client_critic.chat.completions.create(
                                    model=cri_model_name,
                                    messages=[{"role": "user", "content": CRITIC_PROMPT}],
                                    temperature=0.0
                                )
                                critic_feedback = cri_resp.choices[0].message.content
                                
                                if "APPROVED" in critic_feedback.upper():
                                    status.write("🎉 لیست توسط منتقد تایید شد!")
                                    approved = True
                                    final_response = draft_response
                                else:
                                    status.write(f"⚠️ ارور منتقد: {critic_feedback}")
                            else:
                                # اگر منتقد خاموش باشد، همان خروجی اول تایید می‌شود
                                status.write("✅ خروجی تولید شد (سیستم منتقد غیرفعال است).")
                                approved = True
                                final_response = draft_response
                                
                        except Exception as e:
                            status.update(label="❌ خطای ارتباط با مدل", state="error")
                            st.error(f"جزئیات خطا: {e}")
                            break 
                            
                    if not approved:
                        if draft_response != "":
                            status.write("⚠️ حداکثر تلاش‌ها به پایان رسید. نمایش بهترین خروجی موجود...")
                            final_response = draft_response
                        else:
                            status.write("❌ امکان تولید پاسخ وجود نداشت.")
                            final_response = "متاسفانه ارتباط با مدل برقرار نشد."
                    
                    status.update(label="پردازش تمام شد! (مراحل در بالا قابل مشاهده است)", state="complete", expanded=True)
                
                # چاپ خروجی نهایی در صفحه
                st.markdown(final_response)
                
                # ذخیره در دیتابیس
                b_id = save_message(st.session_state.current_session, username, "assistant", final_response)
                st.session_state.messages.append({"id": b_id, "role": "assistant", "content": final_response, "feedback": None})
                
    else:
        st.error("لطفا ابتدا تنظیمات مدل پیشنهاددهنده (API Key یا آدرس Local) را در منوی کناری تکمیل کنید.")