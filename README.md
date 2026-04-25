# 🎬 Smart Movie Recommender with Hybrid RAG

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red.svg)
![AI](https://img.shields.io/badge/AI-Hybrid%20RAG-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---
---

<details>
<summary><strong>🇮🇷 کلیک کنید: نمایش نسخه فارسی (Persian Version)</strong></summary>

<br>

> یک سیستم پیشنهاددهنده فیلم هوشمند با استفاده از مدل‌های زبانی بزرگ (LLMs) و معماری Hybrid RAG، که به طور ویژه برای درک و پیشنهاد فیلم‌های ایرانی و جهانی طراحی شده است.
> 
> ## 🌟 ویژگی‌های کلیدی
> - **معماری Hybrid RAG:** ترکیب پایگاه داده برداری (ChromaDB) برای فیلم‌های محلی و دانش درونی مدل (Parametric Knowledge) برای فیلم‌های جهانی.
> - **پروفایل‌سازی هوشمند کاربر:** تحلیل خودکار تاریخچه چت و استخراج سلیقه سینمایی به عنوان کانتکست (Context).
> - **موتور جستجوی معنایی:** استفاده از مدل‌های `sentence-transformers` چندزبانه برای درک دقیق درخواست‌های فارسی.
> - **پشتیبانی از مدل‌های لوکال و API:** قابلیت اتصال به مدل‌های آفلاین از طریق LM Studio و مدل‌های آنلاین (OpenAI).
> - **خروجی‌گیر پیشرفته:** امکان دانلود تاریخچه پیشنهادات به صورت PDF و TXT.
> - **رابط کاربری تعاملی:** ساخته شده با Streamlit شامل دکمه‌های پیشنهاد سریع و سیستم فیدبک.
> 
> ## 🏛️ معماری سیستم
> 1. **لایه داده:** SQLite برای مدیریت Sessionها و پروفایل کاربران، و ChromaDB برای ذخیره Vector Embeddings.
> 2. **لایه منطق:** پردازش پرامپت‌های هیبریدی (ترکیب RAG و دستورات سیستمی).
> 3. **لایه رابط کاربری:** تعامل روان و زنده (Streaming) با کاربر.
> 
> ## 📚 هدف آکادمیک
> این پروژه به عنوان یک بستر تحقیقاتی برای بررسی تاثیر معماری Hybrid RAG در سیستم‌های پیشنهاددهنده چندزبانه توسعه داده شده است.

</details>

---
---


A smart movie recommendation system built with Large Language Models (LLMs) and a Hybrid RAG (Retrieval-Augmented Generation) architecture, specifically designed to understand and recommend both global and local (Iranian) movies.



---

## 🌟 Key Features
- **Hybrid RAG Architecture:** Combines a Vector Database (ChromaDB) for local/niche movies with the LLM's parametric knowledge for global movies.
- **Smart User Profiling:** Automatically analyzes the user's chat history to extract cinematic preferences and injects them as dynamic context.
- **Semantic Search Engine:** Utilizes multilingual `sentence-transformers` to deeply understand the semantic meaning of user queries.
- **Local & API Model Support:** Seamlessly connects to local offline models via LM Studio or online APIs (e.g., OpenAI GPT).
- **Advanced Export System:** Generates downloadable movie lists in PDF and TXT formats.
- **Interactive UI:** Built with Streamlit, featuring quick-reply buttons, session management, and a Like/Dislike feedback loop.

## 🏛️ System Architecture
The system employs a multi-layered architecture:
1. **Data Layer:** SQLite for session/profile management and ChromaDB for storing plot vector embeddings.
2. **Logic Layer:** Dynamic routing and hybrid prompt engineering to decide between RAG context and LLM intuition.
3. **UI Layer:** Real-time streaming interface with interactive elements.

## 🚀 Installation & Usage

**1. Create a virtual environment and install dependencies:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

**2. Initialize the Vector Database (First Run Only):**
```bash
python build_rag_db.py
```
*Note: This step requires the `dataset.csv` file containing movie metadata and may take a few minutes to process and embed.*

**3. Run the application:**
```bash
streamlit run app.py
```

## 📚 Academic Objective
This project serves as a research platform to evaluate the effectiveness of Hybrid RAG architectures in multilingual recommendation systems, particularly focusing on low-resource languages.

## 📄 License
This project is licensed under the [MIT License](LICENSE).


