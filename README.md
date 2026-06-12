
# 🎬 Smart Movie Recommender with Hybrid RAG & Multi-Agent Architecture

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red.svg)
![AI](https://img.shields.io/badge/AI-Multi--Agent%20System-orange.svg)
![RAG](https://img.shields.io/badge/RAG-Hybrid%20ChromaDB-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

<details>
<summary><strong>🇮🇷 کلیک کنید: نمایش نسخه فارسی (Persian Version)</strong></summary>

<br>

> یک سیستم پیشنهاددهنده فیلم پیشرفته که از ترکیب قدرت **معماری چند-عامله (Multi-Agent)**، **RAG هیبریدی** و **فیلترینگ مشارکتی مبتنی بر هوش مصنوعی** برای ارائه دقیق‌ترین پیشنهادات سینمایی استفاده می‌کند. این پروژه برای مقالات علمی در حوزه سیستم‌های پیشنهاددهنده چندزبانه و مدل‌های زبانی لوکال (SLMs) طراحی شده است.

## 🌟 ویژگی‌های کلیدی
- **فیدبک صریح ۵ ستاره (Explicit Feedback Loop):** سیستم یادگیرنده که امتیازات قبلی کاربر (۱ تا ۵ ستاره) را تحلیل کرده و به صورت خودکار ژانرهای منفور (Blacklist) و محبوب (Whitelist) را در پرامپت‌های بعدی به مدل تزریق می‌کند.
- **پروفایل‌سازی پنهان (Implicit Profiling):** حل مشکل *Cold Start* از طریق تحلیل خودکار تاریخچه چت‌ها در بک‌گراند و ساخت شخصیت سینمایی کاربر.
- **معماری چند-عامله (Generator-Critic):** استفاده از دو عامل هوشمند؛ تولیدکننده (Generator) و منتقد (Critic) با قابلیت تنظیم روی ۳ حالت پردازشی: `Fast` (بدون بازبینی)، `Pro` (یک دور بازبینی) و `Ultra` (حلقه بازبینی سخت‌گیرانه چندمرحله‌ای).
- **معماری Hybrid RAG:** ترکیب پایگاه داده برداری (ChromaDB) برای فیلم‌های ایرانی و دانش درونی مدل (Parametric Knowledge) برای سینمای جهان.
- **معماری Config-Driven و ضد تحریم:** انتقال تمام تنظیمات مدل‌ها و پرامپت‌ها به `config.py` و طراحی یک کلاینت اختصاصی (`requests-based`) برای دور زدن قطعی اختلالات شبکه‌ای و پروکسی‌های ویندوز (Bypass WinError 10061).

## 🏛️ معماری سیستم
1. **لایه داده:** پایگاه داده `SQLite` برای مدیریت نشست‌ها، تاریخچه لایک/دیسلایک و پروفایل‌ها + پایگاه داده برداری `ChromaDB` با مدل امبدینگ `sentence-transformers`.
2. **لایه منطق چند-عامله:** سیستم خوداصلاح‌گر (Self-Correction) که با مهندسی پرامپت مبتنی بر تگ‌های XML هدایت می‌شود.
3. **لایه رابط کاربر:** داشبورد تعاملی Streamlit با سیستم امتیازدهی ۵ ستاره، نمایشگر Badge پردازشی و خروجی‌گیر پیشرفته (PDF/TXT).

## 📚 هدف آکادمیک
این پروژه به عنوان یک بستر تحقیقاتی برای بررسی تاثیر **تزریق تاریخچه تعاملات (Preference Injection)** و **ارزیابی خودکار (Automated Evaluation)** بر کیفیت خروجی مدل‌های زبانی کوچک در محیط‌های ایزوله توسعه یافته است.

</details>

---

A state-of-the-art movie recommendation system that leverages **Multi-Agent Systems (MAS)**, **Hybrid RAG**, and **LLM-Based Explicit Feedback Loops** to deliver highly accurate, rule-compliant, and personalized suggestions.

---

## 🌟 Key Features
- **5-Star Explicit Feedback Loop:** Dynamically learns from user ratings. It uses prompt augmentation to inject historical preferences, automatically blacklisting low-rated genres (1-2 stars) and prioritizing favorites (4-5 stars) in future suggestions.
- **Implicit Profiling Engine:** Solves the *Cold Start* problem by silently summarizing the user's chat history at specific milestones (e.g., messages 2, 5, 10) to construct a persistent "Cinematic Persona".
- **Tiered Multi-Agent Architecture:** Implements a Generator-Critic reasoning loop with 3 execution tiers: `Fast` (zero-shot generation), `Pro` (1-pass critic evaluation), and `Ultra` (iterative, multi-pass strict evaluation).
- **Hybrid RAG Engine:** Merges local vector search (ChromaDB) for niche/Persian cinema with the LLM's internal parametric knowledge for global masterpieces.
- **Proxy-Resilient & Config-Driven:** Fully centralized configuration (`config.py`) and a custom `requests`-based API client designed to completely bypass system-level VPN/Proxy conflicts (e.g., WinError 10061) often encountered with standard libraries.

## 🏛️ System Architecture
The system employs a high-performance multi-layered approach:
1. **Data Layer:** `SQLite` for robust session state, profile retention, and feedback tracking. `ChromaDB` for semantic indexing.
2. **Multi-Agent Logic Layer:** A reasoning loop governed by structured XML instructions, ensuring the SLM adheres strictly to format, language, and logic constraints.
3. **UI Layer:** A streamlined Streamlit dashboard featuring interactive 5-star components, processing mode badges, and instant PDF/TXT export options.

## 🚀 Installation & Usage

**1. Set up the environment:**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

```

**2. Configure the Application:**
Edit `config.py` to match your local/remote LLM settings (ports, API keys, and model names).

**3. Build the Vector Index:**

```bash
python build_rag_db.py

```

**4. Launch the App:**

```bash
streamlit run app.py

```

## 📚 Academic Objective

This project serves as a research platform to evaluate the effectiveness of **Self-Correction Loops**, **Multi-Agent Collaboration**, and **Direct Preference Injection** in improving the zero-shot/few-shot performance of Small Language Models (SLMs) in multilingual environments.

## 🙏 Acknowledgments

Special thanks to **Mohammad** for his valuable [Persian Movie Dataset](https://github.com/mohammad26845/persian_movie_dataset), which was instrumental in building the RAG engine for this project.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
