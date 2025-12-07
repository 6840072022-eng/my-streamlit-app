import streamlit as st 
import pandas as pd
import requests
from bs4 import BeautifulSoup
# import google.generativeai as genai   # ❌ ลบออก
from openai import OpenAI               # ✅ ใช้ OpenAI แทน
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

    /* พื้นหลังหลัก: ขาว → ฟ้าอ่อน (เดิม) */
    .stApp {
        background: linear-gradient(to bottom, #FFFFFF, #DDF3FF);
        color: #000 !important;
    }

    .stApp, .stApp * {
        color: #000 !important;
    }

    /* ---------------------------
       🔥 แก้เฉพาะ sidebar
       --------------------------- */
    section[data-testid="stSidebar"] {
        background-color: #000000 !important; /* sidebar → ดำ */
    }

    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] * {
        color: #FFFFFF !important; /* ตัวอักษร → ขาว */
    }

    section[data-testid="stSidebar"] input {
        background-color: #FFFFFF !important; /* input → ขาว */
        border: 2px solid #000000 !important;
        border-radius: 6px !important;
        color: #000 !important;
    }

    /* Eye icon (password toggle) ทุกตัวใน sidebar → ชมพู */
    section[data-testid="stSidebar"] svg {
        stroke: #FF69B4 !important;
        fill: none !important;
        color: #FF69B4 !important;
    }

    /* ส่วนอื่นๆ ทุกอย่างเดิมตามโค้ดคุณ */
    /* Task type */
    .stSelectbox label {
        background: transparent !important;
    }

    .stSelectbox > div > div {
        background-color: #FFE6F2 !important;
        border: 1.5px solid #000 !important;
        border-radius: 8px !important;
    }

    .stSelectbox [data-baseweb="menu"] {
        background-color: #FFE6F2 !important;
        border: 1px solid #000 !important;
    }

    .stSelectbox [data-baseweb="option"] {
        background-color: #FFE6F2 !important;
        color: #000 !important;
    }

    .stSelectbox [data-baseweb="option"]:hover {
        background-color: #FFCEE6 !important;
    }

    /* Radio */
    .stRadio > div {
        background-color: #FFE6F2 !important;
        border: 1px solid #000 !important;
        padding: 8px;
        border-radius: 8px;
    }

    /* Input fields */
    input, textarea {
        background-color: #FFE6F2 !important;
        border: 1.5px solid #000 !important;
        border-radius: 6px !important;
        color: #000 !important;
    }

    /* Vocabulary Table → ให้พื้นหลังเป็นชมพูทั้งหมด */
    .stDataFrame thead tr th {
        background-color: #FFB6D9 !important;  
        color: #000 !important;
    }

    .stDataFrame tbody tr td {
        background-color: #FFD6EB !important;  
        color: #000 !important;
    }

    /* Buttons */
    button[kind="primary"],
    button[kind="secondary"] {
        background-color: #FF8FC7 !important;
        color: #FFF !important;
        border-radius: 8px !important;
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
# Function: OpenAI generate
# ---------------------------
def openai_generate(api_key, model_name, prompt):
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(layout="wide", page_title="📖 Practice Reading Skills")

st.title("📖 Practice English Reading Skills from a Passage 👓")
st.caption("For learners preparing for TOEIC, IELTS, or English I&II reading tests for arts students.")

st.sidebar.header("Settings")

api_key = st.sidebar.text_input("OpenAI API Key", type="password")

# Input Source
st.subheader("☀️ Input Source")

input_mode = st.radio("Choose input type", ["URL", "Paste text"])

article_text = ""

if input_mode == "URL":
    url = st.text_input("URL (บทความภาษาอังกฤษเช่น BBC, Medium etc.)")
else:
    article_text = st.text_area("Paste your text here (ภาษาอังกฤษเท่านั้น) ", height=250)
    st.session_state.article_text = article_text

# Task select
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

# Run Task
st.subheader("⭐️ Run")

if st.button("Run Task!"):

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
        st.error("Please enter an API key!")
        st.stop()

    if not article_text.strip():
        st.error("No text detected!")
        st.stop()

    # ----- Prompt -----
    if task == "Summarize":
        prompt = f"""
Summarize the following article in:
1) English (6–8 sentences)
2) Thai (6–8 sentences)

Article:
{article_text}
"""

    elif task == "Vocabulary extraction":
        prompt = f"""
Extract vocabulary from the passage below.
Return the result STRICTLY in a markdown table with this format:

| Index | Word | Meaning (TH) | Meaning (EN) | Example sentence |
|-------|-------|--------------|----------------|--------------------|

Article:
{article_text}
"""

    elif task == "Create Cloze Test":
        prompt = f"""
Create a 10-item Cloze Test from the passage.
Use ___ as blanks and show answers at the end.

{article_text}
"""

    elif task == "Reading Comprehension Test":
        prompt = f"""
Create 10 reading comprehension questions (A–D options).
Include Main Idea, Inference, Tone, Vocabulary, etc.
Show answers at the end.

Passage:
{article_text}
"""

    st.info("Processing with OpenAI…")

    try:
        # ⭐⭐⭐ เปลี่ยนเฉพาะตรงนี้ ⭐⭐⭐
        output = openai_generate(api_key, "gpt-4o-mini", prompt)
        # ⭐⭐⭐----------------------⭐⭐⭐

        st.success("Done!")

        # ======================================
        # TABLE PARSER – remove "-----" rows ✔
        # ======================================
        if "|" in output:
            try:
                raw_lines = output.split("\n")

                lines = []
                for line in raw_lines:
                    if "|" not in line:
                        continue

                    cell_parts = [c.strip() for c in line.split("|") if c.strip()]
                    if all(set(c) <= {"-"} for c in cell_parts):
                        continue

                    lines.append(line)

                table_text = "\n".join(lines)

                df = pd.read_csv(
                    io.StringIO(table_text),
                    sep="|",
                    engine="python"
                )

                df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
                df.columns = [c.strip() for c in df.columns]
                df = df.dropna(axis=1, how="all")

                if "Index" in df.columns:
                    df["Index"] = pd.to_numeric(df["Index"], errors="ignore")

                st.dataframe(df, hide_index=True)

                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button("Download CSV", csv_bytes, "result.csv", "text/csv")

            except Exception:
                st.text_area("Output", output, height=420)

        else:
            st.text_area("Output", output, height=420)

    except Exception as e:
        st.error(f"Error: {e}")
