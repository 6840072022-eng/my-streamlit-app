import streamlit as st
import pandas as pd
import requests
import re
from bs4 import BeautifulSoup

from openai import OpenAI
import google.generativeai as genai

st.set_page_config(page_title="Reading Skill AI — TOEIC / IELTS / Arts English", layout="wide")

# -----------------------------
# TITLE AREA
# -----------------------------
st.title("📘 Practicing Reading Skill from a Passage")
st.caption("For learners preparing for TOEIC or IELTS tests, as well as English I & II for Arts students.  
")


# -----------------------------
# SIDEBAR — API SETUP
# -----------------------------
st.sidebar.header("🔑 API Configuration")

api_provider = st.sidebar.radio(
    "เลือก LLM ที่ต้องการใช้",
    ["OpenAI", "Google Gemini"],
)

openai_key = None
gemini_key = None

if api_provider == "OpenAI":
    openai_key = st.sidebar.text_input("ใส่ OpenAI API Key", type="password")
elif api_provider == "Google Gemini":
    gemini_key = st.sidebar.text_input("ใส่ Google Gemini API Key", type="password")


# -----------------------------
# LLM CALLERS
# -----------------------------
def call_openai(prompt: str):
    client = OpenAI(api_key=openai_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You summarize text, extract vocabulary, and generate questions."},
                  {"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content


def call_gemini(prompt: str):
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    return response.text


def ask_llm(prompt: str):
    if api_provider == "OpenAI":
        if not openai_key:
            return "⚠️ กรุณาใส่ OpenAI API Key ก่อน"
        return call_openai(prompt)

    if api_provider == "Google Gemini":
        if not gemini_key:
            return "⚠️ กรุณาใส่ Gemini API Key ก่อน"
        return call_gemini(prompt)


# -----------------------------
# ARTICLE INPUT AREA
# -----------------------------
st.subheader("📥 Input Article")

option = st.radio("เลือกรูปแบบการนำเข้าข้อมูล", ["URL", "Upload CSV/Excel"])

article_text = ""

if option == "URL":
    url = st.text_input("วาง URL ของบทความภาษาอังกฤษที่ต้องการสรุปที่นี่ (ยกตัวอย่างเช่น บทความจาก BBC, Medium, The Guardian เป็นต้น)")

    if st.button("ดึงบทความจาก URL"):
        try:
            raw_html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
            soup = BeautifulSoup(raw_html, "html.parser")
            paragraphs = soup.find_all("p")
            article_text = " ".join(p.get_text(strip=True) for p in paragraphs)
            st.success("ดึงบทความสำเร็จ!")
        except:
            st.error("ไม่สามารถโหลด URL นี้ได้")

elif option == "Upload CSV/Excel":
    file = st.file_uploader("อัปโหลดไฟล์ CSV หรือ Excel", type=["csv", "xlsx"])
    if file:
        try:
            if file.name.endswith(".csv"):
                df_input = pd.read_csv(file)
            else:
                df_input = pd.read_excel(file)
            article_text = " ".join(df_input.astype(str).stack())
            st.success("โหลดข้อมูลสำเร็จ!")
            st.dataframe(df_input)
        except:
            st.error("ไฟล์ไม่สามารถอ่านได้")


# -----------------------------
# PROCESSING BUTTONS
# -----------------------------
if article_text:
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        gen_summary = st.button("📝 สรุปบทความ")
    with col2:
        gen_vocab = st.button("📚 ดึงคำศัพท์")
    with col3:
        gen_questions = st.button("🧪 สร้างคำถามจับใจความ")

    # OUTPUT AREA
    st.markdown("---")

    if gen_summary:
        output = ask_llm(f"Summarize this article:\n\n{article_text}")
        st.subheader("📝 สรุปบทความ")
        st.write(output)

    if gen_vocab:
        output = ask_llm(
            f"Extract important English vocabulary from this article. "
            f"Return JSON list with fields: word, meaning, example."
            f"\n\nArticle:\n{article_text}"
        )
        st.subheader("📚 คำศัพท์สำคัญ")
        st.write(output)

    if gen_questions:
        output = ask_llm(
            f"Generate 5 English reading comprehension questions from this passage:\n{article_text}"
        )
        st.subheader("🧪 แบบทดสอบจับใจความ")
        st.write(output)


