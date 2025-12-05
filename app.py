import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import io

# ---------------------------
# Background Image
# ---------------------------
st.image(
    "https://i.postimg.cc/tJq9xYC3/IMG-0520.png",
    use_column_width=True
)

# ---------------------------
# CSS Styling (ปรับใหม่)
# ---------------------------
st.markdown("""
<style>

/* ---------------------
   MAIN BACKGROUND
----------------------*/
.stApp {
    background: linear-gradient(to bottom, #FFFFFF, #DDF3FF);
    color: #000 !important;
}
.stApp, .stApp * {
    color: #000 !important;
}

/* ---------------------
   SIDEBAR
----------------------*/
section[data-testid="stSidebar"] {
    background-color: #FFE6F2 !important;
    border-right: 2px solid #000 !important;
}

section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea,
section[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #FFE6F2 !important;
    border: 1.5px solid #000 !important;
    border-radius: 6px !important;
}

/* ปุ่มรูป "ตา" – show/hide password */
section[data-testid="stSidebar"] svg {
    color: #3FA9F5 !important;  /* ฟ้า */
}

/* ---------------------
   SELECTBOX
----------------------*/
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
}
.stSelectbox [data-baseweb="option"]:hover {
    background-color: #FFCEE6 !important;
}

/* ---------------------
   RADIO
----------------------*/
.stRadio > div {
    background-color: #FFE6F2 !important;
    border: 1px solid #000 !important;
    padding: 8px;
    border-radius: 8px;
}

/* ---------------------
   DATAFRAME – Pink theme
----------------------*/
div[data-testid="stDataFrame"] thead th {
    background-color: #FFC7E3 !important;
    color: #000 !important;
}
div[data-testid="stDataFrame"] tbody td {
    background-color: #FFE6F2 !important;
    color: #000 !important;
}
div[data-testid="stDataFrame"] {
    background-color: #FFE6F2 !important;
}

/* ---------------------
   BUTTONS
----------------------*/
button[kind="primary"],
button[kind="secondary"] {
    background-color: #FF8FC7 !important;
    color: #FFF !important;
    border-radius: 8px !important;
}

</style>
""", unsafe_allow_html=True)

# ---------------------------
# Initialize session state
# ---------------------------
if "article_text" not in st.session_state:
    st.session_state.article_text = ""

# ---------------------------
# Function: Fetch URL
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
        texts = " ".join(a.get_text(" ", strip=True) for a in article_tags)
    else:
        paragraphs = soup.find_all("p")
        texts = " ".join(p.get_text(" ", strip=True) for p in paragraphs)

    texts = " ".join(texts.split())
    return texts if texts.strip() else None, None

# ---------------------------
# Gemini
# ---------------------------
def gemini_generate(api_key, model_name, prompt):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text

# ---------------------------
# UI
# ---------------------------
st.set_page_config(layout="wide", page_title="📖 Practice Reading Skills")

st.title("📖 Practice Reading Skills from a Passage 👓")
st.caption("For learners preparing for TOEIC, IELTS, or English I&II reading tests.")

st.sidebar.header("Settings")

api_key = st.sidebar.text_input("Google Gemini API Key", type="password")

model_name = st.sidebar.selectbox(
    "Model",
    ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
)

# Input source
st.subheader("☀️ Input Source")

input_mode = st.radio("Choose input type", ["URL", "Paste text"])
article_text = ""

if input_mode == "URL":
    url = st.text_input("URL (BBC, Medium etc.)")
else:
    article_text = st.text_area("Paste your text here", height=250)
    st.session_state.article_text = article_text

# Task
st.subheader("🌈 Select Task")

task = st.selectbox(
    "Task type",
    ["Summarize", "Vocabulary extraction", "Create Cloze Test", "Reading Comprehension Test"]
)

# Run
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
        st.error("Please enter an API key!")
        st.stop()

    if not article_text.strip():
        st.error("No text detected!")
        st.stop()

    # PROMPTS
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
Return the result **strictly in a markdown table**:

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
Show answers at the end.

Passage:
{article_text}
"""

    st.info("Processing with Gemini…")

    try:
        output = gemini_generate(api_key, model_name, prompt)
        st.success("Done!")

        # ===============================
        # CLEAN TABLE FOR VOCAB
        # ===============================
        if "|" in output:
            try:
                raw_lines = output.split("\n")
                lines = []

                for line in raw_lines:
                    if "|" not in line:
                        continue

                    # skip separator e.g. |-----|-----|
                    parts = [c.strip() for c in line.split("|") if c.strip()]
                    if all(set(c) <= {"-"} for c in parts):
                        continue

                    lines.append(line)

                table_txt = "\n".join(lines)

                df = pd.read_csv(io.StringIO(table_txt), sep="|", engine="python")
                df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
                df.columns = [c.strip() for c in df.columns]
                df = df.dropna(axis=1, how="all")

                st.dataframe(df, hide_index=True)

                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button("Download CSV", csv_bytes, "result.csv", "text/csv")

            except Exception:
                st.text_area("Output", output, height=420)

        else:
            st.text_area("Output", output, height=420)

    except Exception as e:
        st.error(f"Error: {e}")
