import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import time
import base64

# -----------------------------
#  CONFIG
# -----------------------------

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key="


# -----------------------------
#  CORE FUNCTIONS
# -----------------------------

def call_gemini(system_prompt, user_prompt, api_key):
    """เรียก Google Gemini API"""
    if not api_key:
        return None  # ไม่เรียก API ถ้าไม่มีคีย์

    try:
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
        }

        url = API_BASE + api_key
        response = requests.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดระหว่างเรียก Gemini API: {e}")
        return None


def extract_article(url):
    """ดึงเนื้อหาจากเว็บไซต์"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        for tag in ["script", "style", "header", "footer", "nav", "img"]:
            for x in soup.find_all(tag):
                x.decompose()

        article = soup.find("article") or soup.find("main") or soup.find("body")
        text = "\n".join([p.get_text().strip() for p in article.find_all("p")])

        title = soup.title.string if soup.title else url

        return title, text

    except Exception as e:
        return None, f"❌ ไม่สามารถดึงเนื้อหาได้: {e}"


def df_download(df, filename):
    """สร้างปุ่มดาวน์โหลด CSV"""
    csv = df.to_csv(index=False).encode()
    b64 = base64.b64encode(csv).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">⬇️ ดาวน์โหลด CSV</a>'
    st.markdown(href, unsafe_allow_html=True)


# -----------------------------
#       MAIN APP UI
# -----------------------------

def main():
    st.set_page_config(page_title="NLP App (LLM)", layout="wide")
    st.title("📘 NLP Web App with Google Gemini")

    # Sidebar
    with st.sidebar:
        st.header("🔑 API Settings")
        api_key = st.text_input("Gemini API Key (optional)", type="password")
        st.caption("ถ้าไม่กรอก → ระบบจะทำงานแบบไม่ใช้ LLM ได้ตามปกติ")

        st.markdown("---")
        st.header("📝 วิธีใช้งาน")
        st.write(
            """
            ✔ ป้อน URL หรืออัปโหลดไฟล์ CSV/Excel  
            ✔ ถ้าใส่ API Key → เปิดโหมด LLM (Summarization, Entity Extraction, etc.)
            ✔ ถ้าไม่ใส่ → ใช้งานเฉพาะการดึงเนื้อหาได้
        """
        )

    # Tabs
    tab1, tab2 = st.tabs(["🌍 อ่านจาก URL", "📁 อัปโหลด CSV/Excel"])

    article_text = None
    article_title = None

    # ---------------------------
    # OPTION 1 — URL
    # ---------------------------
    with tab1:
        url = st.text_input("ใส่ URL บทความ")
        if st.button("ดึงเนื้อหา"):
            title, text = extract_article(url)
            if text:
                article_title = title
                article_text = text
                st.success(f"📌 ดึงเนื้อหาได้: {title}")
                st.code(text[:1000] + "..." if len(text) > 1000 else text)

    # ---------------------------
    # OPTION 2 — CSV / Excel
    # ---------------------------
    with tab2:
        file = st.file_uploader("อัปโหลด CSV หรือ Excel", type=["csv", "xlsx"])
        if file:
            df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)
            st.dataframe(df, use_container_width=True)
            article_text = "\n".join(df.iloc[:, 0].astype(str).tolist())
            article_title = "ข้อมูลจากไฟล์"

    # ---------------------------
    #  NLP TASKS (ใช้ LLM)
    # ---------------------------
    if article_text:

        st.markdown("---")
        st.header("✨ NLP Tasks")

        if not api_key:
            st.warning("⚠️ ไม่พบ API Key — โหมด LLM ถูกปิด\nแต่คุณยังอ่านเนื้อหาได้ตามปกติ")
            return

        # -------- Task 1 Summary -------
        st.subheader("📝 Task 1 — Summarization")
        system_1 = "คุณเป็นผู้เชี่ยวชาญด้านการสรุปเนื้อหา ให้สรุปบทความให้อ่านเข้าใจง่ายใน 5–10 ประโยค"
        output_1 = call_gemini(system_1, article_text, api_key)
        if output_1:
            st.write(output_1)

        # -------- Task 2 Entity Extraction -------
        st.subheader("🧩 Task 2 — Entity Extraction (JSON)")
        system_2 = """
            คุณเป็น NLP Model ให้ดึง Entities หลักในบทความนี้:
            - Person
            - Organization
            - Location
            - Date
            และตอบกลับเป็น JSON array เช่น:
            [{"entity":"Google","type":"Organization"}]
        """
        json_text = call_gemini(system_2, article_text, api_key)
        try:
            df_entities = pd.DataFrame(json.loads(json_text))
            st.dataframe(df_entities)
            df_download(df_entities, "entities.csv")
        except:
            st.error("ผลลัพธ์ไม่สามารถแปลงเป็น JSON ได้")

        # -------- Task 3 Sentiment -------
        st.subheader("😊 Task 3 — Deep Sentiment Analysis")
        system_3 = """
            วิเคราะห์อารมณ์เชิงลึกของบทความให้ละเอียดมาก:
            - อารมณ์หลัก (Primary Emotion)
            - อารมณ์รอง (Secondary Emotion)
            - แรงจูงใจของผู้เขียน
            - น้ำเสียง (Tone)
            - คะแนน Sentiment (-5 = ลบมาก, 5 = บวกมาก)
        """
        output_3 = call_gemini(system_3, article_text, api_key)
        if output_3:
            st.write(output_3)


if __name__ == "__main__":
    main()
