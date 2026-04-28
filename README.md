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

> یک سیستم پیشنهاددهنده فیلم پیشرفته که از ترکیب قدرت **معماری چند-عامله (Multi-Agent)** و **RAG هیبریدی** برای ارائه دقیق‌ترین پیشنهادات سینمایی استفاده می‌کند. این پروژه برای مقالات علمی در حوزه سیستم‌های پیشنهاددهنده چندزبانه و مدل‌های زبانی لوکال طراحی شده است.

## 🌟 ویژگی‌های کلیدی
- **معماری چند-عامله (Generator-Critic):** استفاده از دو عامل هوشمند؛ یکی برای تولید پیشنهاد (Generator) و دیگری برای ارزیابی و اصلاح خروجی (Critic) بر اساس قوانین کاربر.
- **معماری Hybrid RAG:** ترکیب پایگاه داده برداری (ChromaDB) برای فیلم‌های محلی/ایرانی و دانش درونی مدل (Parametric Knowledge) برای سینمای جهان.
- **انعطاف‌پذیری در اتصال مدل‌ها:** قابلیت اجرای ۵ حالت مختلف (فقط لوکال، فقط API، ترکیب لوکال-لوکال، ترکیب API-API و حالت هیبریدی لوکال-API).
- **مهندسی پرامپت پیشرفته (XML-Based):** استفاده از تگ‌های ساختاریافته برای کنترل دقیق مدل‌های لوکال و جلوگیری از لو رفتن دستورات سیستم (Prompt Leakage).
- **تحلیل هوشمند رفتار کاربر:** استخراج خودکار پروفایل سلیقه سینمایی کاربر از تاریخچه چت‌ها برای شخصی‌سازی دقیق پیشنهادات.
- **شفافیت پردازش:** نمایش زنده مراحل "همفکری" و "ارزیابی" بین عوامل هوش مصنوعی در رابط کاربری.

## 🏛️ معماری سیستم
1. **لایه داده:** SQLite برای مدیریت نشست‌ها و ChromaDB با استفاده از `sentence-transformers` چندزبانه.
2. **لایه منطق چند-عامله:** یک حلقه تکرار شونده (Iterative Loop) که در آن منتقد دستورات اصلاحی را به تولیدکننده ارسال می‌کند تا خروجی به استانداردهای مطلوب برسد.
3. **لایه رابط کاربر:** پیاده‌سازی شده با Streamlit برای تعامل بلادرنگ و خروجی‌های PDF/TXT.

## 📚 هدف آکادمیک
این پروژه به عنوان یک بستر تحقیقاتی برای بررسی تاثیر **ارزیابی خودکار (Automated Evaluation)** بر کیفیت خروجی مدل‌های زبانی کوچک (SLMs) در محیط‌های محدود (Local) توسعه یافته است.

</details>

---

A state-of-the-art movie recommendation system that leverages **Multi-Agent Systems (MAS)** and **Hybrid RAG** to deliver highly accurate, rule-compliant, and personalized suggestions.

---

## 🌟 Key Features
- **Multi-Agent Architecture (Generator-Critic):** Implements a sophisticated loop where a **Generator Agent** drafts suggestions and a **Critic Agent** audits them for language accuracy, movie count, and formatting.
- **Hybrid RAG Engine:** Merges local vector search (ChromaDB) for niche/Persian cinema with the LLM's internal knowledge for global masterpieces.
- **Universal Connectivity:** Supports 5 distinct execution modes:
    - Pure Local (LM Studio)
    - Pure API (OpenAI)
    - Dual Local (Different models for Generator/Critic)
    - Dual API (High-end model as Critic)
    - Hybrid (Local Generator + API Critic)
- **Structured Prompt Engineering:** Employs XML-tagging and Few-Shot prompting to maximize reasoning capabilities in Local LLMs and prevent prompt leakage.
- **LLM-Based User Profiling:** Dynamically analyzes chat history to construct a persistent "Cinematic Persona" for each user.
- **Thought Visualization:** Real-time monitoring of agent debates and reasoning steps within the UI.

## 🏛️ System Architecture
The system employs a high-performance multi-layered approach:
1. **Data Layer:** SQLite for session management and user profiles; ChromaDB for semantic indexing of movie plots.
2. **Multi-Agent Logic Layer:** A reasoning loop governed by structured instructions, where the Critic provides corrective feedback to the Generator until constraints are met.
3. **UI Layer:** An interactive Streamlit dashboard supporting real-time streaming and advanced data export (PDF/TXT).

## 🚀 Installation & Usage

**1. Set up the environment:**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**2. Build the Vector Index:**
```bash
python build_rag_db.py
```

**3. Launch the App:**
```bash
streamlit run app.py
```

## 📚 Academic Objective
This project serves as a research platform to evaluate the effectiveness of **Self-Correction Loops** and **Multi-Agent Collaboration** in improving the output quality of Small Language Models (SLMs) in multilingual contexts.

## 📄 License
This project is licensed under the [MIT License](LICENSE).