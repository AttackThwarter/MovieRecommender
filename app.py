import streamlit as st

# -- تنظیمات اولیه صفحه --
st.set_page_config(page_title="دستیار پیشنهاد فیلم", page_icon="🎬")
st.title("🎬 پیشنهاددهنده هوشمند فیلم")

# -- ایجاد حافظه موقت --
# اگر حافظه پیام‌ها خالی بود، یک لیست خالی برایش می‌سازیم
if "messages" not in st.session_state:
    st.session_state.messages = []

# -- نمایش تاریخچه پیام‌ها --
# تمام پیام‌های قبلی را روی صفحه می‌آورد
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# -- بخش گرفتن پیام از کاربر --
# کادر پایین صفحه که کاربر توش تایپ میکنه
if prompt := st.chat_input("چه سبک فیلمی دوست داری؟ یا چه حسی داری؟"):
    
    # ۱. نمایش پیام کاربر روی صفحه
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # ۲. ذخیره پیام کاربر در حافظه
    st.session_state.messages.append({"role": "user", "content": prompt})

    # ۳. نمایش یک جواب آزمایشی از سمت دستیار (بعداً با LLM جایگزین می‌شود)
    fake_response = "سلام! من هنوز به هوش مصنوعی وصل نشدم، اما به زودی بهترین فیلم‌ها رو بهت پیشنهاد می‌دم!"
    with st.chat_message("assistant"):
        st.markdown(fake_response)
        
    # ۴. ذخیره جواب دستیار در حافظه
    st.session_state.messages.append({"role": "assistant", "content": fake_response})