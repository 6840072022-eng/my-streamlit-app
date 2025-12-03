import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Article Summary & Vocabulary App", layout="wide")
st.title("📰 แอปสรุปบทความภาษาอังกฤษ + คำศัพท์ + แบบทดสอบ")

# -------------------------------
# ฟังก์ชันดึงบทความจาก URL
# -------------------------------
def extract_article(url):
    try:
        page = requests.get(url, timeout=10)
        soup = BeautifulSoup(page.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = " ".join([p.get_text() for p in paragraphs])
        return text.strip()
    except:
        return ""

# -------------------------------
# ฟังก์ชันสรุปบทความ (Mock)
# -------------------------------
def summarize_text(text):
    # ตรงนี้ควรเชื่อม LLM จริง แต่ตอนนี้เป็น mock
    return "This is a summary of the article. (Mock)"

# -------------------------------
# ฟังก์ชันแตกคำศัพท์จากบทความ (Mock)
# -------------------------------
def extract_vocab(text):
    data = {
        "คำศัพท์": ["global", "impact", "economy", "sustainability"],
        "ความหมาย": ["relating to the whole world", "effect or influence", "system of trade and money", "ability to be maintained"],
        "ประโยคตัวอย่าง": [
            "Climate change has a global impact.",
            "The new law had a huge impact on workers.",
            "The economy is recovering slowly.",
            "Sustainability is important for future generations."
        ]
    }
    return pd.DataFrame(data)

# -------------------------------
# สร้างคำถามทดสอบ (Mock)
# -------------------------------
def generate_questions(text):
    return [
        "What is the main idea of the article?",
        "Which factor influences the issue discussed?",
        "What is one example mentioned in the article?"
    ]

# -------------------------------
# UI ส่วนให้ผู้ใช้ใส่ URL
# -------------------------------
st.header("🔗 ใส่ลิงก์บทความภาษาอังกฤษที่ต้องการสรุป")
url = st.text_input("วาง URL ที่นี่")

if st.button("ดึงบทความจากลิงก์", key="load_url"):
    article = extract_article(url)
    if article:
        st.session_state.article = article
        st.success("โหลดบทความสำเร็จแล้ว!")
    else:
        st.error("ไม่สามารถโหลดบทความได้ กรุณาตรวจสอบลิงก์อีกครั้ง")

# ถ้ามีบทความแล้ว
if "article" in st.session_state:
    st.subheader("📄 บทความที่ดึงมา")
    st.write(st.session_state.article[:1500] + "...")

    # ปุ่มสรุป
    if st.button("สรุปบทความ", key="summarize"):
        summary = summarize_text(st.session_state.article)
        st.session_state.summary = summary
        st.success("สรุปเสร็จแล้ว!")

    # แสดงสรุป
    if "summary" in st.session_state:
        st.subheader("📝 สรุปบทความ")
        st.write(st.session_state.summary)

        # ปุ่มแตกคำศัพท์
        if st.button("แยกคำศัพท์สำคัญ", key="vocab"):
            vocab_df = extract_vocab(st.session_state.article)
            st.session_state.vocab = vocab_df
            st.success("แยกคำศัพท์สำเร็จแล้ว!")

    # แสดงคำศัพท์
    if "vocab" in st.session_state:
        st.subheader("📚 คำศัพท์สำคัญจากบทความ")
        st.dataframe(st.session_state.vocab)

        st.download_button(
            "ดาวน์โหลดตารางคำศัพท์ (CSV)",
            st.session_state.vocab.to_csv(index=False),
            file_name="vocabulary.csv"
        )

        # ปุ่มสร้างแบบทดสอบ
        if st.button("สร้างแบบทดสอบจับใจความ (ภาษาอังกฤษ)", key="quiz"):
            qs = generate_questions(st.session_state.article)
            st.session_state.questions = qs
            st.success("สร้างคำถามเสร็จแล้ว!")

    # แสดงคำถาม
    if "questions" in st.session_state:
        st.subheader("🧪 แบบทดสอบจับใจความ")
        for i, q in enumerate(st.session_state.questions, 1):
            st.write(f"**Q{i}. {q}**")
