import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import io

# ---------------------------
# Page Config
# ---------------------------
st.set_page_config(layout="wide", page_title="📘 AI Reading & Vocabulary Tool")

# ---------------------------
# Header Image + Style
# ---------------------------
st.image("https://i.postimg.cc/tJq9xYC3/IMG-0520.png", use_column_width=True)

st.markdown(
    """
    <style>

    .stApp {
        background: linear-gradient(to bottom, #FFFFFF, #DDF3FF);
        color: #000 !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #FFE6F2 !important;
        border-right: 2px solid #000 !important;
    }

    /* Sidebar Inputs */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {
        background-color: #FFE6F2 !important;
        border: 1.5px solid #000 !important;
        border-radius: 6px !important;
        color: #000 !important;
    }

    /* Eye icon */
    input[type="password"] + div svg {
        stroke: #0099FF !important;
        color: #0099FF !important;
    }

    /* DataFrame Styling */
    .stDataFrame thead tr th {
        background-color: #FFB6D9 !important;
        color: #000 !important;
    }
    .stDataFrame tbody tr td {
        background-color: #FFD6EB !important;
        color: #000 !important;
    }

    button[kind="primary"], button[kind="secondary"] {
        background-color: #FF8FC7 !important;
        color: white !important;
        border-radius: 8px !important;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# Sidebar
# ---------------------------
st.sidebar.header("🔐 API Settings")

openai_api = st.sidebar.text_input("OpenAI API Key", type="password")
gemini_api = st.sidebar.text_input("Google Gemini API Key", type="password")

st.sidebar.info("จำเป็นต้องกรอก Gemini API เพื่อใช้งาน Generate")

# ---------------------------
# Input section
# ---------------------------
st.title("📘 AI Reading Tools – Summarize, Vocabulary, Cloze Test")

st.subheader("📝 Choose Input Source")

input_method = st.radio(
    "Input type",
    ["Paste text", "URL", "Upload CSV/Excel"]
)

article_text = ""

# Text input
if input_method == "Paste text":
    article_text = st.text_area("Paste your article text", height=250)

# URL fetcher
elif input_method == "URL":
    url = st.text_input("Enter article URL")
    if url:
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            paras = soup.find_all("p")
            article_text = " ".join([p.get_text(strip=True) for p in paras])
            st.success("Text extracted from URL!")
            st.text_area("Extracted Text", article_text, height=200)
        except:
            st.error("Failed to fetch content.")

# File upload
elif input_method == "Upload CSV/Excel":
    uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])
    df = None
    if uploaded:
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)

        st.write("📄 File Loaded:")
        st.dataframe(df)

        if st.checkbox("Use first column as text input"):
            article_text = " ".join(df.iloc[:, 0].astype(str).tolist())

# ---------------------------
# Select task
# ---------------------------
st.subheader("📚 Task")

task = st.selectbox(
    "Choose task",
    ["Summarize", "Vocabulary extraction", "Create Cloze Test", "Reading Comprehension Test"]
)

# ---------------------------
# Prompt builder
# ---------------------------
def build_prompt(task, text):
    if task == "Summarize":
        return f"""
Summarize the following article in English and Thai.  
English: 6–8 sentences  
Thai: 6–8 sentences  

Article:
{text}
"""

    if task == "Vocabulary extraction":
        return f"""
Extract vocabulary from the passage below.

Return the result STRICTLY as a markdown table with EXACTLY 5 columns:

| Index | Word | Meaning (TH) | Meaning (EN) | Example sentence |
|-------|-------|--------------|--------------|------------------|

Rules:
1. NO bold, NO italic, NO markdown formatting in table cells.
2. PLAIN TEXT ONLY.
3. Every row must have exactly 5 columns.
4. Do not add text outside the table.

Article:
{text}
"""

    if task == "Create Cloze Test":
        return f"""
Create a 10-item Cloze Test from this passage.
Use ___ for blanks.
Show the answer key at the end.

{text}
"""

    if task == "Reading Comprehension Test":
        return f"""
Create 10 reading comprehension questions (A–D choices).
Include main idea, inference, detail, tone, and vocabulary.
Show answer key at the end.

Passage:
{text}
"""

# ---------------------------
# Gemini Function
# ---------------------------
def gemini_generate(api_key, model_name, prompt):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    result = model.generate_content(prompt)
    return result.text

# ---------------------------
# Run
# ---------------------------
st.subheader("🚀 Run Task")

if st.button("Run Now"):
    if not gemini_api:
        st.error("Please enter Gemini API Key!")
        st.stop()

    if not article_text.strip():
        st.error("No input text provided!")
        st.stop()

    prompt = build_prompt(task, article_text)

    st.info("Processing with Gemini…")
    output = gemini_generate(gemini_api, "gemini-2.0-flash", prompt)

    # Try table parse
    if task == "Vocabulary extraction" and "|" in output:
        try:
            raw_lines = output.split("\n")
            cleaned = []

            for line in raw_lines:
                if "|" not in line:
                    continue
                parts = [c.strip() for c in line.split("|") if c.strip()]
                if all(set(p) <= {"-"} for p in parts):
                    continue
                cleaned.append(line)

            fixed = []
            for row in cleaned:
                r = row.strip()
                if r.startswith("|"):
                    r = r[1:]
                if r.endswith("|"):
                    r = r[:-1]
                fixed.append(r)

            text_csv = "\n".join([r.replace("|", ",") for r in fixed])

            df = pd.read_csv(io.StringIO(text_csv))
            st.dataframe(df, hide_index=True)

            st.download_button(
                "Download CSV",
                df.to_csv(index=False).encode("utf-8"),
                "vocab.csv",
                "text/csv"
            )

        except Exception as e:
            st.warning("Could not parse table. Showing raw output.")
            st.text_area("Output", output, height=450)

    else:
        st.text_area("Output", output, height=450)
