import os
import csv
import time
import requests
import random

# --- دور زدن فیلترشکن ---
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

import config
from database import get_golden_examples
import chromadb
from chromadb.utils import embedding_functions

# ==========================================
# ⚙️ تنظیمات آزمایشگاه (آزمون ۵۰ نفره)
# ==========================================
NUM_TESTS = 50
OUTPUT_FILE = "evaluation_results_detailed.csv"
TEST_QUERY = "۳ فیلم ایرانی و ۲ فیلم خارجی به من پیشنهاد بده."
MODEL_USED = "gemma-3-12b-it-qat (Local)"

# --- تولید خودکار ۵۰ سلیقه متنوع (Synthetic Personas) ---
base_tastes = [
    "من عاشق فیلم‌های اکشن و هیجان‌انگیز هستم، اما از فیلم‌های درام، آرام و عاشقانه به شدت متنفرم.",
    "من فقط فیلم‌های کمدی و خنده‌دار دوست دارم. اصلا حوصله فیلم‌های معمایی، ترسناک یا پیچیده را ندارم.",
    "من طرفدار سینمای هنر و تجربه، فیلم‌های روان‌شناختی و پایان‌باز هستم. کمدی‌های سطحی را دوست ندارم.",
    "من به فیلم‌های تاریخی و بیوگرافی علاقه دارم و دلم می‌خواهد فیلم‌هایی با امتیاز بسیار بالا ببینم.",
    "من عاشق فیلم‌های علمی‌تخیلی و فانتزی با جلوه‌های ویژه خیره‌کننده هستم.",
    "من فیلم‌های ترسناک و دلهره‌آور دوست دارم. اصلا فیلم‌های کمدی یا عاشقانه به من پیشنهاد نده.",
    "فقط فیلم‌های جنایی، معمایی و کارآگاهی که تا لحظه آخر قاتل مشخص نباشد.",
    "من یک درام خانوادگی و اجتماعی می‌خوام که مشکلات واقعی جامعه رو نشون بده."
]
modifiers = [
    "لطفاً فیلم‌هایی با امتیاز بالای ۷ پیشنهاد بده.",
    "خیلی سخت‌گیرم و دنبال شاهکارهای سینمایی هستم.",
    "دوست دارم داستان فیلم ریتم تندی داشته باشه.",
    "از فیلم‌های خیلی طولانی خوشم نمیاد.",
    "ترجیح میدم کارگردان‌های معروف فیلم رو ساخته باشن."
]

PERSONAS = []
for i in range(NUM_TESTS):
    taste = base_tastes[i % len(base_tastes)]
    mod = random.choice(modifiers)
    PERSONAS.append(f"{taste} {mod}")

random.shuffle(PERSONAS) # مخلوط کردن لیست کاربران

# ==========================================
# 🛠️ توابع ارتباط با مدل
# ==========================================
def call_llm(messages, temperature=0.3):
    url = f"{config.GEN_BASE_URL}/chat/completions"
    headers = {"Content-Type": "application/json"}
    payload = {"model": config.GEN_MODEL_NAME, "messages": messages, "temperature": temperature}
    proxies = {"http": None, "https": None}
    try:
        response = requests.post(url, json=payload, headers=headers, proxies=proxies, timeout=120)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"ERROR: {e}"

def simulate_rag(query):
    try:
        client = chromadb.PersistentClient(path=config.CHROMA_DB_DIR)
        emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=config.EMBEDDING_MODEL_NAME)
        collection = client.get_collection(name="iranian_movies", embedding_function=emb_fn)
        results = collection.query(query_texts=[query], n_results=5)
        context = ""
        for i in range(len(results['documents'][0])):
            context += f"▪️ {results['documents'][0][i]}\n"
        return context
    except:
        return "دیتابیس آفلاین است."

# ==========================================
# 🧠 پرامپت‌های ارزیابی داور
# ==========================================
BASELINE_PROMPT = "تو یک دستیار سینمایی هستی. به درخواست کاربر پاسخ بده و فیلم معرفی کن."

# JUDGE_PROMPT = """تو یک داور علمی و سخت‌گیر هستی.
# سلیقه و شخصیت کاربر: "{persona}"
# درخواست کاربر: "۳ فیلم ایرانی و ۲ فیلم خارجی به من پیشنهاد بده."

# خروجی سیستم A (سنتی):
# {output_a}

# خروجی سیستم B (پیشنهادی):
# {output_b}

# به عنوان این کاربر، خروجی‌ها را بررسی کن. 
# ابتدا دلیل خود را در یک پاراگراف بنویس، سپس نمره‌ها را (از ۱ تا ۵) بده.
# فرمت خروجی تو باید دقیقاً اینگونه باشد:
# REASONING: [تحلیل شما]
# SCORE_A: [نمره از 1 تا 5]
# SCORE_B: [نمره از 1 تا 5]
# """

JUDGE_PROMPT = """تو یک داور علمی و سخت‌گیر هستی.
سلیقه و شخصیت کاربر: "{persona}"
درخواست کاربر: "۳ فیلم ایرانی و ۲ فیلم خارجی به من پیشنهاد بده."

خروجی سیستم A (سنتی):
{output_a}

خروجی سیستم B (پیشنهادی):
{output_b}

وظیفه تو ارزیابی این دو خروجی بر اساس ۳ معیار کلیدی زیر است:
۱. همخوانی با سلیقه (Personalization): آیا فیلم‌ها دقیقاً با سلیقه و خط قرمزهای کاربر مطابقت دارند؟
۲. زیبایی و فرمت‌بندی (Formatting): آیا خروجی ساختار منظم، خوانا و جذابی (مثل استفاده از ایموجی، لیست‌بندی و بولد کردن) دارد؟
۳. دقت (Accuracy): آیا فیلم‌ها و نام‌ها واقعی و منطقی به نظر می‌رسند یا مدل آن‌ها را توهم زده است؟

ابتدا خروجی‌ها را بر اساس این ۳ معیار مقایسه و تحلیل کن (در یک پاراگراف کامل).
سپس بر اساس تحلیل خود، به هر سیستم یک نمره کلی (از ۱ تا ۵) بده.

فرمت خروجی تو باید دقیقاً اینگونه باشد:
REASONING: [تحلیل دقیق شما بر اساس ۳ معیار]
SCORE_A: [نمره از 1 تا 5]
SCORE_B: [نمره از 1 تا 5]
"""

# ==========================================
# 📊 تابع رسم نمودارهای علمی (Data Visualization)
# ==========================================
def generate_academic_charts(csv_file):
    print("\n" + "="*50)
    print("📈 در حال رسم نمودارهای تحلیلی و ذخیره آن‌ها...")
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns

    df = pd.read_csv(csv_file)
    
    # تنظیم استایل
    sns.set_theme(style="whitegrid")
    
    # ۱. نمودار مقایسه میانگین رضایت
    plt.figure(figsize=(10, 6))
    mean_a = df['Baseline_Score'].mean()
    mean_b = df['Proposed_Score'].mean()
    
    ax = sns.barplot(x=['Baseline (Zero-Shot)', 'Proposed Method (RLAIF + RAG)'], 
                     y=[mean_a, mean_b], palette=['#e74c3c', '#2ecc71'])
    
    plt.title('Average User Satisfaction Score', fontsize=16, fontweight='bold', pad=20)
    plt.suptitle(f'Model Used: {MODEL_USED} | N={len(df)} Synthetic Users', fontsize=10, color='gray')
    plt.ylim(0, 5.5)
    plt.ylabel('Average Score (1 to 5 Stars)', fontsize=12)
    
    for p in ax.patches:
        ax.annotate(f'{p.get_height():.2f}', 
                    (p.get_x() + p.get_width() / 2., p.get_height()), 
                    ha='center', va='center', xytext=(0, 10), textcoords='offset points', fontweight='bold', fontsize=14)
    
    plt.savefig('Chart_1_Satisfaction_Comparison.png', dpi=300, bbox_inches='tight')
    plt.close()

    # ۲. نمودار مقایسه زمان پردازش (Latency)
    plt.figure(figsize=(10, 6))
    time_data = pd.DataFrame({
        'System': ['Baseline (Zero-Shot)', 'Proposed Method (RLAIF + RAG)'],
        'Average Latency (sec)': [df['Time_A_sec'].mean(), df['Time_B_sec'].mean()]
    })
    ax2 = sns.barplot(x='System', y='Average Latency (sec)', data=time_data, palette=['#3498db', '#f39c12'])
    plt.title('Processing Time Comparison (Latency Trade-off)', fontsize=16, fontweight='bold', pad=20)
    plt.suptitle(f'Model Used: {MODEL_USED}', fontsize=10, color='gray')
    plt.ylabel('Seconds', fontsize=12)
    
    for p in ax2.patches:
        ax2.annotate(f'{p.get_height():.1f}s', 
                    (p.get_x() + p.get_width() / 2., p.get_height()), 
                    ha='center', va='center', xytext=(0, 10), textcoords='offset points', fontweight='bold', fontsize=14)
        
    plt.savefig('Chart_2_Latency_Comparison.png', dpi=300, bbox_inches='tight')
    plt.close()

    # ۳. توزیع نمرات (Score Distribution)
    plt.figure(figsize=(12, 6))
    df_melted = pd.melt(df, value_vars=['Baseline_Score', 'Proposed_Score'], 
                        var_name='System', value_name='Score')
    df_melted['System'] = df_melted['System'].replace({'Baseline_Score': 'Baseline', 'Proposed_Score': 'Proposed (RLAIF)'})
    
    sns.countplot(x='Score', hue='System', data=df_melted, palette=['#e74c3c', '#2ecc71'])
    plt.title('Distribution of 1 to 5 Star Ratings', fontsize=16, fontweight='bold', pad=20)
    plt.suptitle(f'Model Used: {MODEL_USED}', fontsize=10, color='gray')
    plt.xlabel('Star Rating')
    plt.ylabel('Number of Users')
    plt.legend(title='Architecture')
    
    plt.savefig('Chart_3_Score_Distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("✅ رسم نمودارها تمام شد! سه فایل تصویر (png) در پوشه پروژه ذخیره شدند.")


# ==========================================
# 🚀 اجرای آزمایشگاه و A/B Testing (نسخه ضدگلوله)
# ==========================================
def run_evaluation():
    print(f"🧪 شروع فاز ارزیابی دقیق روی {NUM_TESTS} کاربر (این پروسه حدود {NUM_TESTS*4} دقیقه زمان می‌برد)...")
    rag_context = simulate_rag(TEST_QUERY)
    golden_examples = get_golden_examples(limit=2)

    fieldnames = ["User_ID", "Persona", "Baseline_Score", "Proposed_Score", "Time_A_sec", "Time_B_sec", "Judge_Reasoning", "Response_A_Raw", "Response_B_Raw"]
    
    # ساخت فایل اولیه و نوشتن هِدِر (عناوین ستون‌ها)
    with open(OUTPUT_FILE, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

    for i in range(NUM_TESTS):
        current_persona = PERSONAS[i]
        print(f"\n[{i+1}/{NUM_TESTS}] 👤 شبیه‌سازی کاربر: {current_persona}")
        
        try:
            # --- سیستم A ---
            print("   ⏳ پردازش سیستم A...")
            start_a = time.time()
            output_a = call_llm([{"role": "system", "content": BASELINE_PROMPT}, {"role": "user", "content": TEST_QUERY}], temperature=0.5)
            time_a = round(time.time() - start_a, 2)
            time.sleep(5) # استراحت کوتاه

            # --- سیستم B ---
            print("   ⏳ پردازش سیستم B...")
            proposed_prompt = config.GEN_PROMPT_TEMPLATE.format(
                user_style=current_persona, rating_history="کاربر جدید است.", golden_examples=golden_examples, rag_context=rag_context, feedback_section=""
            )
            start_b = time.time()
            output_b = call_llm([{"role": "system", "content": proposed_prompt}, {"role": "user", "content": TEST_QUERY}], temperature=0.3)
            time_b = round(time.time() - start_b, 2)
            time.sleep(5) # استراحت کوتاه

            # --- داوری ---
            print("   ⚖️ در حال داوری استدلالی...")
            judge_prompt_formatted = JUDGE_PROMPT.format(persona=current_persona, output_a=output_a, output_b=output_b)
            judge_decision = call_llm([{"role": "user", "content": judge_prompt_formatted}], temperature=0.1)
            
            score_a, score_b = 0, 0
            reasoning = "نامشخص"
            
            lines = judge_decision.split('\n')
            reasoning_lines = []
            for line in lines:
                if line.startswith("SCORE_A:"):
                    score_a = int(''.join(filter(str.isdigit, line)))
                elif line.startswith("SCORE_B:"):
                    score_b = int(''.join(filter(str.isdigit, line)))
                elif not line.startswith("SCORE"):
                    reasoning_lines.append(line.replace("REASONING:", "").strip())
            reasoning = " ".join(reasoning_lines).strip()

            print(f"   ⏱️ زمان A: {time_a}s | زمان B: {time_b}s")
            print(f"   🏆 نمره A: {score_a} | نمره B: {score_b}")
            
            # 💾 ذخیره قطره‌چکانی (Append) در همان لحظه
            row_data = {
                "User_ID": i+1,
                "Persona": current_persona,
                "Baseline_Score": score_a,
                "Proposed_Score": score_b,
                "Time_A_sec": time_a,
                "Time_B_sec": time_b,
                "Judge_Reasoning": reasoning,
                "Response_A_Raw": output_a,
                "Response_B_Raw": output_b
            }
            with open(OUTPUT_FILE, mode='a', newline='', encoding='utf-8-sig') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writerow(row_data)
            print("   💾 [دیتا ذخیره شد]")

            # 🛌 استراحت بلندمدت برای خنک شدن GPU بعد از هر ۵ تست
            if (i + 1) % 5 == 0:
                print("   🛌 [استراحت ۱۵ ثانیه‌ای سیستم برای جلوگیری از افت فریم و داغ شدن گرافیک...]")
                time.sleep(60)
            else:
                time.sleep(40)

        except Exception as e:
            print(f"   ❌ خطا در تست کاربر {i+1}: {e}")
            continue

    print("\n✅ پردازش تمام شد!")
    
    # فراخوانی تابع رسم نمودارها
    generate_academic_charts(OUTPUT_FILE)

if __name__ == "__main__":
    run_evaluation()