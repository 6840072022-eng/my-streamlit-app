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

    /* พื้นหลัง: ขาวด้านบน ไล่ไปฟ้าอ่อนด้านล่าง */
    .stApp {
        background: linear-gradient(to bottom, #FFFFFF, #DDF3FF);
        height: 100vh;
        color: #000000 !important;
    }

    /* ตัวอักษรทั้งหมดเป็นสีดำ */
    .stApp, .stApp * {
        color: #000000 !important;
    }

    /* กล่อง input ต่าง ๆ */
    .stTextInput textarea,
    .stTextInput input,
    textarea,
    input,
    .stSelectbox div[data-baseweb="select"],
    .stRadio,
    .stSelectbox {
        background-color: rgba(255, 255, 255, 0.7) !important;
        color: #000000 !important;
    }

    /* DataFrame header */
    .stDataFrame thead tr th {
        background-color: rgba(200, 230, 255, 0.8) !important;
        color: #000000 !important;
    }

    /* เซลล์ใน DataFrame */
    .stDataFrame tbody tr td {
        background-color: rgba(255, 255, 255, 0.6) !important;
        color: #000000 !important;
    }

    /* ปุ่ม */
    button[kind="primary"] {
        background-color: #2089E5 !important;
        color: #FFFFFF !important;
    }
    button[kind="secondary"] {
        background-color: #888 !important;
        color: #FFFFFF !important;
    }

    /* placeholder */
    ::placeholder {
        color: #555555 !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] * {
        color: #000000 !important; 
    }

    section[data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.4) !important;
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
# Function: Gemini call (AUTO TOKEN MODE)
# ---------------------------
def gemini_generate(api_key, model_name, prompt):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
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
