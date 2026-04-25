import pandas as pd
import chromadb
from chromadb.utils import embedding_functions

print("🚀 در حال راه‌اندازی سیستم پایگاه داده برداری...")

# ۱. ساخت کلاینت دیتابیس برداری (این دیتابیس روی هارد شما در پوشه chroma_db ذخیره می‌شود)
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# ۲. انتخاب مدل هوش مصنوعی برای تبدیل متن به عدد (Embedding)
# نکته مهم برای مقاله: چون دیتای ما فارسی است، از یک مدل چندزبانه (Multilingual) استفاده می‌کنیم
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

# ۳. ایجاد یک کالکشن (مثل یک جدول در دیتابیس)
collection = chroma_client.get_or_create_collection(
    name="iranian_movies", 
    embedding_function=emb_fn
)

print("📚 در حال خواندن فایل CSV...")
# ۴. خواندن دیتاست با Pandas
df = pd.read_csv("dataset.csv")

# فیلتر کردن ردیف‌هایی که خلاصه داستان فارسی یا اسم فارسی ندارند (تمیز کردن دیتا)
df = df.dropna(subset=['Content_1', 'PERSIAN_title'])

documents = []
metadatas = []
ids = []

print("🧠 در حال پردازش فیلم‌ها و تبدیل به بردارهای ریاضی (ممکن است چند دقیقه طول بکشد)...")
# ۵. حلقه زدن روی تک‌تک فیلم‌ها
for index, row in df.iterrows():
    # الف) ساخت یک متن غنی برای فهم مدل
    text_for_ai = f"عنوان فیلم: {row['PERSIAN_title']}\nژانر: {row['Genre']}\nداستان: {row['Content_1']}"
    documents.append(text_for_ai)
    
    # ب) ذخیره اطلاعات جانبی (Metadata) تا بعدا بتونیم تو خروجی چاپشون کنیم
    metadatas.append({
        "persian_title": str(row['PERSIAN_title']),
        "english_title": str(row['EN_title']),
        "year": str(row['Year']),
        "score": str(row['Score'])
    })
    
    # ج) یک آیدی یکتا برای هر فیلم
    ids.append(f"movie_{index}")

# ۶. تزریق تمام داده‌ها به دیتابیس برداری
collection.add(
    documents=documents,
    metadatas=metadatas,
    ids=ids
)

print(f"✅ با موفقیت {len(documents)} فیلم به پایگاه داده برداری اضافه شد!")
print("پوشه chroma_db در کنار فایل‌های شما ساخته شد. دیگر نیازی به اجرای مجدد این اسکریپت نیست.")