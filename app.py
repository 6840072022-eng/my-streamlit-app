import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import io

# ---------------------------
# Background Image / Gradient
# ---------------------------

st.image(
    "https://i.postimg.cc/tJq9xYC3/IMG-0520.png",
    use_column_width=True
)

st.markdown(
    """
    <style>
    .stApp {
        /* ไล่สีเข้มจากบนลงล่าง */
        background: linear-gradient(to bottom, #0F2027, #203A43, #2C5364);
        height: 100vh;
    }

    /* ปรับสีตัวอักษรให้อ่านง่าย */
    .stApp .block-container {
        color: #FFFFFF;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# Initialize session state
# ---------------------------
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
st.set_page_config(layout="wide", page_title="📖 Practice Reading Skills")

# Title & Caption
st.title("📖 Practice Reading Skills from a Passage 👓")
st.caption("For learners preparing for TOEIC, IELTS, or English I&II reading tests for arts students.")

# Sidebar
st.sidebar.header("Settings")

api_key = st.sidebar.text_input("Google Gemini API Key", type="password")

model_name = st.sidebar.selectbox(
    "Model",
    ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
)

max_tokens = st.sidebar.slider("Max output tokens", 128, 4096, 1024, 128)

# Input options
st.subheader("☀️ Input Source")

input_mode = st.radio("Choose input type", ["URL", "Paste text"])

article_text = ""

if input_mode == "URL":
    url = st.text_input("URL (ใส่ลิงก์บทความภาษาอังกฤษจากเว็บ เช่น BBC, Medium etc.)")
else:
    article_text = st.text_area("Paste your text here", height=250)
    st.session_state.article_text = article_text

# Tasks
st.subheader("🌈 Select Task")

task = st.selectbox(
    "Task type",
    [
        "Summarize",
        "Vocabulary extraction",
        "Create Cloze Test",
        "Reading Comprehension Test"
    ]
)

# Run Button
st.subheader("⭐️ Run")

if st.button("Run Task"):

    if not article_text.strip():
        article_text = st.session_state.article_text

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

    # ---- Create prompt ----
    if task == "Summarize":
        prompt = f"""
You are a bilingual summarizer.

Please summarize the following article in TWO versions:

1) English Summary (6–8 sentences)
2) Thai Summary (6–8 sentences)

Article:
{article_text}
"""

    elif task == "Vocabulary extraction":
        prompt = f"""
คุณคือระบบดึงคำศัพท์ภาษาอังกฤษ
โปรดดึงคำศัพท์สำคัญจากบทความด้านล่าง
Return as a table with 5 columns:
Index | Word | Meaning (TH) | Meaning (EN) | Example sentence

{article_text}
"""

    elif task == "Create Cloze Test":
        prompt = f"""
สร้างแบบทดสอบ Cloze test จากบทความด้านล่าง
ให้ 10 ข้อ มีช่องว่าง ___ และเฉลยท้ายสุด

{article_text}
"""

    elif task == "Reading Comprehension Test":
        prompt = f"""
สร้างแบบทดสอบ Reading comprehension จำนวน 10 ข้อ
ครอบคลุมหัวข้อ Main Idea, Purpose, Detail, Inference, Vocabulary, T/F, Tone
เป็น Multiple Choice 4 ตัวเลือก A-D
เฉลยท้ายสุดแบบนี้: 1) A 2) C 3) B ...

บทความ:

{article_text}
"""

    # ---- Run Gemini ----
    st.info("Processing with Gemini…")

    try:
        output = gemini_generate(api_key, model_name, prompt, max_tokens=max_tokens)
        st.success("Done!")

        if "|" in output:
            try:
                # อ่าน DataFrame
                df = pd.read_csv(io.StringIO(output), sep="|", header=0, skipinitialspace=True)

                # ลบคอลัมน์ Unnamed
                df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

                # สำหรับ Vocabulary extraction ให้แสดงเฉพาะ 5 คอลัมน์
                if task == "Vocabulary extraction":
                    expected_cols = ['Index', 'Word', 'Meaning (TH)', 'Meaning (EN)', 'Example sentence']
                    cols_to_use = [c for c in expected_cols if c in df.columns]
                    df = df[cols_to_use]

                    # ถ้าไม่มี Index ให้สร้างเอง
                    if 'Index' not in df.columns:
                        df.insert(0, 'Index', range(1, len(df)+1))

                st.dataframe(df)

                # ดาวน์โหลด CSV
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button("Download CSV", csv_bytes, "result.csv", "text/csv")

            except Exception as e:
                st.text_area("Output", output, height=400)
        else:
            st.text_area("Output", output, height=400)

    except Exception as e:
        st.error(f"Error: {e}")
