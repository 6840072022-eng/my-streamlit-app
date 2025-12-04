import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# ---------------------------
# CONFIG
# ---------------------------
st.title("📝 Article Analysis with Gemini")

gemini_api = st.text_input("ใส่ Google API Key", type="password")
url = st.text_input("ใส่ลิงก์บทความที่ต้องการวิเคราะห์")

# ---------------------------
# Function: scrape article
# ---------------------------
def extract_article(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        # ดึง text ทุก <p>
        paragraphs = soup.find_all("p")
        text = "\n".join([p.get_text() for p in paragraphs])

        return text.strip()

    except Exception as e:
        return None


# ---------------------------
# When pressing RUN
# ---------------------------
if st.button("วิเคราะห์บทความ"):
    if not gemini_api:
        st.error("❌ กรุณาใส่ API Key")
        st.stop()

    if not url:
        st.error("❌ กรุณาใส่ URL")
        st.stop()

    # Extract article
    article_text = extract_article(url)

    if not article_text:
        st.error("❌ ไม่พบเนื้อหาบทความ หรือไม่สามารถดึงข้อมูลได้")
        st.stop()

    st.success("ดึงบทความสำเร็จ!")
    st.write("**ตัวอย่างเนื้อหาที่ดึงได้:**")
    st.write(article_text[:500] + " ...")

    # ---------------------------
    # Run Gemini
    # ---------------------------
    genai.configure(api_key=gemini_api)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
    วิเคราะห์และสรุปบทความต่อไปนี้ให้กระชับ อ่านง่าย และเข้าใจเร็ว:

    {article_text}
    """

    with st.spinner("กำลังวิเคราะห์ด้วย Gemini..."):
        response = model.generate_content(prompt)

    st.subheader("📌 สรุปบทความ")
    st.write(response.text)
