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

    /* พื้นหลังหลัก */
    .stApp {
        background: linear-gradient(to bottom, #FFFFFF, #DDF3FF);
        color: #000 !important;
    }

    .stApp, .stApp * {
        color: #000 !important;
    }

    /* ------------------------------------ */
    /* Sidebar → ดำ ตัวอักษรขาว */
    /* ------------------------------------ */
    section[data-testid="stSidebar"] {
        background-color: #000 !important;
        border-right: 2px solid #FFF !important;
        color: #FFF !important;
    }

    section[data-testid="stSidebar"] * {
        color: #FFF !important;
    }

    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea,
    section[data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: #333 !important;
        border: 1.5px solid #FFF !important;
        color: #FFF !important;
    }

    /* ------------------------------ */
    /* 🔥 กล่อง URL + Paste text = ชมพูกรอบดำ */
    /* ------------------------------ */
    textarea, input[type="text"] {
        background-color: #FFD6EB !important;
        border: 2px solid #000 !important;
        color: #000 !important;
        border-radius: 8px !important;
    }

    /* ------------------------------ */
    /* 🔥 Output box = ชมพูกรอบดำ */
    /* ------------------------------ */
    .stTextArea textarea {
        background-color: #FFD6EB !important;
        border: 2px solid #000 !important;
        color: #000 !important;
        border-radius: 8px !important;
    }

    /* Eye Icon */
    input[type="password"] + div svg,
    [data-testid="stPasswordInput"] svg {
        stroke: #0099FF !important;
        color: #0099FF !important;
    }

    /* Table Header */
    .stDataFrame thead tr th {
        background-color: #FFB6D9 !important;
        color: #000 !important;
    }

    /* Table Body */
    .stDataFrame tbody tr td {
        background-color: #FFD6EB !important;
        color: #000 !important;
    }

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
# Function: Gemini generate
# ---------------------------
def gemini_generate(api_key, prompt):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(layout="wide", page_title="📖 Practice Reading Skills")

st.title("📖 Practice Reading Skills from a Passage 👓")
st.caption("For learners preparing for TOEIC, IELTS, or English I&II reading tests for arts students.")

st.sidebar.header("Settings")

# No model select
api_key = st.sidebar.text_input("Google Gemini API Key", type="password")

# -------------------------------------------------
# Input Source
# -------------------------------------------------
st.subheader("☀️ Input Source")

input_mode = st.radio("Choose input type", ["URL", "Paste text"])

article_text = ""

if input_mode == "URL":
    url = st.text_input("URL (BBC, Medium etc.)")
else:
    article_text = st.text_area("Paste your text here", height=250)
    st.session_state.article_text = article_text

# -------------------------------------------------
# Task select
# -------------------------------------------------
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

# -------------------------------------------------
# Run Task
# -------------------------------------------------
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

    st.info("Processing with Gemini…")

    try:
        output = gemini_generate(api_key, prompt)
        st.success("Done!")

        # ===========================
        # SAFE TABLE PARSER
        # ===========================
        if "|" in output:
            try:
                raw = output.split("\n")

                clean = []
                for line in raw:
                    if "|" not in line:
                        continue

                    parts = [c.strip() for c in line.split("|") if c.strip()]
                    if all(set(p) <= {"-"} for p in parts):
                        continue

                    clean.append(line.strip())

                if len(clean) < 2:
                    raise ValueError("Not a table")

                fixed = []
                for row in clean:
                    r = row
                    if r.startswith("|"):
                        r = r[1:]
                    if r.endswith("|"):
                        r = r[:-1]
                    fixed.append(r)
                fixed_text = "\n".join(fixed)

                df = pd.read_csv(
                    io.StringIO(fixed_text.replace("|", ",")),
                    engine="python"
                )

                df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
                df.columns = [c.strip() for c in df.columns]

                st.dataframe(df, hide_index=True)

                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button("Download CSV", csv_bytes, "result.csv", "text/csv")

            except Exception:
                st.text_area("Output", output, height=420)

        else:
            st.text_area("Output", output, height=420)

    except Exception as e:
        st.error(f"Error: {e}")
