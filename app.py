import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import io

# Initialize session state
if "article_text" not in st.session_state:
    st.session_state.article_text = ""

# ---------------------------
# Function: Fetch article text
# ---------------------------
def fetch_article_text(url):
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as e:
        return None, f"Error fetching URL: {e}"

    soup = BeautifulSoup(resp.text, "html.parser")

    article_tags = soup.find_all(["article"])
    if article_tags:
        texts = " ".join(a.get_text(separator=" ", strip=True) for a in article_tags)
    else:
        paragraphs = soup.find_all("p")
        texts = " ".join(p.get_text(separator=" ", strip=True) for p in paragraphs)

    texts = " ".join(texts.split())
    return texts if texts.strip() else None, None


# ---------------------------
# Function: Gemini call
# ---------------------------
def gemini_generate(api_key, model_name, prompt, max_tokens=1024):
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(model_name)

    response = model.generate_content(
        prompt,
        generation_config={"max_output_tokens": max_tokens}
    )

    return response.text


# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(layout="wide", page_title="NLP Analyzer (Gemini)")

st.title("📖 Practice Reading Skills from the Passage 👓")

# Sidebar
st.sidebar.header("Settings")

api_key = st.sidebar.text_input("Google Gemini API Key", type="password")

model_name = st.sidebar.selectbox(
    "Model",
    ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
)

max_tokens = st.sidebar.slider("Max output tokens", 128, 4096, 1024, 128)

# Input options
st.subheader("📚 Input source แปะแหล่งบทความที่ต้องการวิเคราะห์ ")

input_mode = st.radio("Choose input type ",
                      ["URL (ลิงก์จากบทความเช่น BBC, Medium or etc.)",
                       "Paste text (แปะข้อความที่ต้องการเลือก)"])

article_text = ""

if input_mode == "URL":
    url = st.text_input("Enter article URL")
else:
    article_text = st.text_area("Paste your text here", height=250)
    st.session_state.article_text = article_text


# Tasks
st.subheader("📚 Select Task เลือกคำสั่งที่ต้องการ")

task = st.selectbox(
    "Task type",
    [
        "☆彡 Summarize วิเคราะห์สรุปจากบทความ ",
        "☆彡 Vocabulary extraction ตารางศัพท์จากบทความ",
        "☆彡 Translate to French แปลบทความ",
        "☆彡 Create Cloze Test แบบฝึกหัดเติมคำจากบทความ",
        "☆彡 Reading Comprehension Test แบบฝึกหัดจับใจความ (ช้อยส์) "
    ]
)

# Run Button
st.subheader("📚 Run")

if st.button("Run Task !"):

    if not article_text.strip():
        article_text = st.session_state.article_text

    # Auto-fetch for URL
    if input_mode == "URL" and url.strip() and not article_text.strip():
        text, err = fetch_article_text(url)
        if err:
            st.error(err)
            st.stop()
        article_text = text
        st.session_state.article_text = text

    if not api_key:
        st.error("Please enter an API key in the sidebar!")
        st.stop()

    if not article_text.strip():
        st.error("No input text detected!")
        st.stop()

    # ---- Create prompt based on task ----
    if task == "☆彡 Summarize วิเคราะห์สรุปจากบทความ ":
        prompt = f"""
You are a bilingual summarizer.

Please summarize the following article in TWO versions:

1) **English Summary (6–8 sentences)**
2) **Thai Summary (6–8 sentences)**

Article:
{article_text}
"""

    elif task == "☆彡 Vocabulary extraction ตารางศัพท์จากบทความ":
        prompt = f"""
คุณคือระบบดึงคำศัพท์ภาษาอังกฤษ
โปรดดึงคำศัพท์สำคัญจากบทความด้านล่าง
พร้อม (คำศัพท์ | ความหมายไทย | ตัวอย่างประโยค)

Return as a table:

{article_text}
"""

    elif task == "☆彡 Translate to French แปลบทความ":
        prompt = f"""
แปลข้อความต่อไปนี้เป็นภาษาฝรั่งเศสแบบเป็นธรรมชาติ:

{article_text}
"""

    elif task == "☆彡 Create Cloze Test แบบฝึกหัดเติมคำจากบทความ":
        prompt = f"""
สร้างแบบทดสอบ Cloze test จากบทความด้านล่าง
ให้ 10 ข้อ แต่ละข้อมีช่องว่าง ___ และคำตอบท้ายสุด

บทความ:

{article_text}
"""

    elif task == "☆彡 Reading Comprehension Test แบบฝึกหัดจับใจความ (ช้อยส์) ":
        prompt = f"""
คุณคือระบบสร้างแบบทดสอบ Reading comprehension ระดับมหาวิทยาลัย  
จากบทความด้านล่างนี้ ให้สร้างคำถามทั้งหมด 10 ข้อ  
โดยประกอบด้วยหัวข้อต่อไปนี้อย่างน้อยอย่างละ 1 ข้อ:

- Main Idea
- Main Purpose
- Detail
- Inference
- Vocabulary in Context
- True/False
- Tone / Attitude (ถ้ามี)

รูปแบบคำถาม:
- Multiple Choice 4 ตัวเลือก: A, B, C, D  
- ตัวเลือกต้อง plausible และใกล้เคียงกัน  
- เฉลยอยู่ท้ายสุดแบบนี้:
Answer Key: 1) A  2) C  3) B ...

บทความ:
{article_text}
"""

    # ---- Call Gemini ----
    st.info("Processing with Gemini…")

    try:
        output = gemini_generate(api_key, model_name, prompt, max_tokens=max_tokens)
        st.success("Done!")

        # Try rendering table
        if "|" in output:
            try:
                df = pd.read_csv(io.StringIO(output), sep="|")
                st.dataframe(df)
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button("Download CSV", csv_bytes, "result.csv", "text/csv")
            except:
                st.text_area("Output", output, height=400)
        else:
            st.text_area("Output", output, height=400)

    except Exception as e:
        st.error(f"Error: {e}")
