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

st.title("NLP Analyzer with Google Gemini")

# Sidebar
st.sidebar.header("Settings")

api_key = st.sidebar.text_input("Google Gemini API Key", type="password")

model_name = st.sidebar.selectbox(
    "Model",
    ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
)

max_tokens = st.sidebar.slider("Max output tokens", 128, 4096, 1024, 128)

# Input options
st.subheader("1) Input Source")

input_mode = st.radio("Choose input type", ["URL", "Paste text"])

article_text = ""

if input_mode == "URL":
    url = st.text_input("Enter article URL")

    if st.button("Fetch article text"):
        if not url.strip():
            st.warning("Please enter a valid URL")
        else:
            text, err = fetch_article_text(url)
            if err:
                st.error(err)
            else:
                article_text = text
                st.session_state.article_text = text      # <-- ⭐ FIX #1
                st.success("Fetched successfully!")
                st.text_area("Article Preview", article_text[:2000], height=250)

else:
    article_text = st.text_area("Paste your text here", height=250)
    st.session_state.article_text = article_text          # <-- ⭐ FIX #2


# Tasks
st.subheader("2) Select Task")

task = st.selectbox(
    "Task type",
    [
        "Summarize",
        "Vocabulary extraction",
        "Translate to French",
        "Create Cloze Test",
        "Generate Slogans"
    ]
)

# Run Button
st.subheader("3) Run")

if st.button("Run Task"):

    # ⭐ FIX #3 โหลดค่าจาก session state ถ้า article_text ว่าง
    if not article_text.strip():
        article_text = st.session_state.article_text

    # ⭐ FIX #4 กัน None
    article_text = article_text or ""

    if not api_key:
        st.error("Please enter an API key in the sidebar!")
    elif not article_text.strip():
    
    # ⭐ ถ้า input เป็น URL → auto-fetch ให้เลย ไม่ต้องกดปุ่ม Fetch
        if input_mode == "URL" and url.strip():
            text, err = fetch_article_text(url)
            if err:
                st.error(err)
                st.stop()
            st.session_state.article_text = text
            article_text = text
        else:
            st.error("No input text detected!")
            st.stop()
    else:

        # ---- Create prompt based on task ----
        if task == "Summarize":
            prompt = f"""
คุณคือระบบสรุปบทความขั้นสูง
โปรดสรุปข้อความต่อไปนี้ให้กระชับ ชัดเจน อ่านง่าย:

{article_text}
"""

        elif task == "Vocabulary extraction":
            prompt = f"""
คุณคือระบบดึงคำศัพท์ภาษาอังกฤษ
โปรดดึงคำศัพท์สำคัญจากบทความด้านล่าง
พร้อม (คำศัพท์ | ความหมายไทย | ตัวอย่างประโยค)

Return as a table:

{article_text}
"""

        elif task == "Translate to French":
            prompt = f"""
แปลข้อความภาษาไทยต่อไปนี้เป็นภาษาฝรั่งเศสแบบเป็นธรรมชาติ:

{article_text}
"""

        elif task == "Create Cloze Test":
            prompt = f"""
สร้างแบบทดสอบ Cloze test จากบทความด้านล่าง
ให้ 10 ข้อ แต่ละข้อมีช่องว่าง ___ และคำตอบท้ายสุด

บทความ:

{article_text}
"""

        elif task == "Generate Slogans":
            prompt = f"""
สร้างสโลแกนสินค้า 20 แบบ โดยอิงจากข้อมูลนี้:

{article_text}

ให้ผลลัพธ์เป็นรายการ bullet points
"""

        # ---- Call Gemini ----
        st.info("Processing with Gemini…")

        try:
            output = gemini_generate(api_key, model_name, prompt, max_tokens=max_tokens)
            st.success("Done!")

            # Try reading as table for DataFrame output
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

