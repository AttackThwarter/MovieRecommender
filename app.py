import streamlit as st
from openai import OpenAI

# -- ۱. تنظیمات اولیه صفحه --
st.set_page_config(page_title="دستیار پیشنهاد فیلم", page_icon="🎬")
st.title("🎬 پیشنهاددهنده هوشمند فیلم")

# -- ۲. منوی تنظیمات (سایدبار) --
st.sidebar.title("⚙️ تنظیمات مدل")
# یک دکمه رادیویی برای انتخاب بین لوکال و API
model_type = st.sidebar.radio("کدام مدل را می‌خواهید استفاده کنید؟", ["لوکال (LM Studio)", "OpenAI API"])

# تنظیم متغیرها بر اساس انتخاب کاربر
if model_type == "لوکال (LM Studio)":
    st.sidebar.info("ابتدا نرم‌افزار LM Studio را باز کرده و Local Server آن را استارت بزنید.")
    base_url = st.sidebar.text_input("آدرس سرور لوکال:", value="http://localhost:1234/v1")
    api_key = "lm-studio" # برای مدل لوکال هر متنی بنویسیم قبول می‌کند
    model_name = "local-model" 
else:
    base_url = "https://api.openai.com/v1"
    api_key = st.sidebar.text_input("کلید API خود را وارد کنید:", type="password")
    model_name = st.sidebar.text_input("نام مدل (مثل gpt-3.5-turbo):", value="gpt-3.5-turbo")

# ساخت کلاینت (رابط) برای اتصال به مدل
client = None
if api_key:
    client = OpenAI(base_url=base_url, api_key=api_key)

# -- ۳. حافظه و پرامپت سیستم --
if "messages" not in st.session_state:
    # این همان پرامپت پنهانی است که به مدل می‌گوید چه کاره است (بعدا پیشرفته‌ترش می‌کنیم)
    # system_prompt = "شما یک متخصص حرفه ای سینما و پیشنهاددهنده فیلم هستید. با کاربر به زبان فارسی و دوستانه صحبت کنید. ابتدا سلیقه او را بپرسید و سپس ۳ فیلم جذاب پیشنهاد دهید."
    
    # -- ۳. حافظه و پرامپت سیستم --
    if "messages" not in st.session_state:
        # یک پرامپت حرفه‌ای و چند خطی برای هدایت دقیق مدل
        system_prompt = """
        تو یک دستیار هوشمند، صمیمی و متخصص در زمینه پیشنهاد فیلم (Movie Recommender) هستی.
        زبان اصلی تو برای ارتباط با کاربر "فارسی" است.
        
        وظایف تو به این ترتیب است:
        ۱. اگر کاربر فقط سلام کرد یا درخواست نامشخصی داشت، با لحنی دوستانه از او بپرس که چه ژانری دوست دارد، یا الان چه حسی دارد (مثلا خسته است، هیجان‌زده است و...).
        ۲. وقتی سلیقه کاربر را فهمیدی، دقیقا ۳ فیلم باکیفیت و متناسب با سلیقه او پیشنهاد بده.
        ۳. خروجی تو حتما باید با فرمت زیر (و استفاده از ایموجی) باشد:
        
        🎬 **[نام انگلیسی فیلم]** ([سال تولید])
        🎭 **ژانر:** [ژانر فیلم]
        💡 **چرا این فیلم؟** [در یک خط توضیح بده که چرا این فیلم به سلیقه کاربر می‌خورد]
        ---
        
        نکته مهم: به هیچ وجه اطلاعات اضافه، کدهای برنامه‌نویسی یا متن‌های طولانی تولید نکن. فقط تمرکزت روی پیشنهاد فیلم با فرمت بالا باشد.
        """
    
    st.session_state.messages = [{"role": "system", "content": system_prompt}]

    # پیام اول همیشه نقش system دارد و به کاربر نشان داده نمی‌شود
    st.session_state.messages = [{"role": "system", "content": system_prompt}]

# -- ۴. نمایش تاریخچه پیام‌ها روی صفحه --
for message in st.session_state.messages:
    if message["role"] != "system": # پیام سیستم را به کاربر نشان نده
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# -- ۵. دریافت پیام کاربر و ارسال به مدل --
if prompt := st.chat_input("چه سبک فیلمی دوست داری؟ یا چه حسی داری؟"):
    
    # نمایش پیام کاربر
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # ذخیره در حافظه
    st.session_state.messages.append({"role": "user", "content": prompt})

    # اگر کلاینت به درستی تنظیم شده بود، به مدل وصل شو
    if client:
        with st.chat_message("assistant"):
            try:
                # ارسال کل تاریخچه مکالمه به مدل برای گرفتن جواب
                response = client.chat.completions.create(
                    model=model_name,
                    messages=st.session_state.messages,
                    temperature=0.7 # میزان خلاقیت مدل (بین صفر تا یک)
                )
                
                # استخراج متن جواب از خروجی مدل
                bot_response = response.choices[0].message.content
                st.markdown(bot_response)
                
                # ذخیره جواب مدل در حافظه
                st.session_state.messages.append({"role": "assistant", "content": bot_response})
                
            except Exception as e:
                st.error(f"❌ خطا در ارتباط با مدل. لطفاً تنظیمات را چک کنید. متن خطا: {e}")
    else:
        st.warning("⚠️ لطفاً ابتدا تنظیمات سایدبار را تکمیل کنید.")