# app.py
# VERSIONS: Mock LLM — no external API required.
# NOTE: For production with real LLM replace mock functions with API calls.
#
# If you deploy on Streamlit Cloud, add a requirements.txt with:
# streamlit
# requests
# beautifulsoup4
# pandas

import streamlit as st
import requests
import re
import io
import pandas as pd
from collections import Counter
from typing import List, Dict

st.set_page_config(page_title="สรุปบทความ + คำศัพท์ + แบบทดสอบ (Mock)", layout="wide")
st.title("📘 Practicing Reading Skill from a Passage")
st.caption("ยกตัวอย่างเช่น บทความจาก BBC, Medium, The Guardian, National Geographic เป็นต้น")


# -----------------------
# Helpers: safe extraction
# -----------------------
def fetch_html(url: str, timeout=10) -> str:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.text
    except Exception as e:
        return ""

def extract_text_from_html(html: str) -> str:
    # Try BeautifulSoup if available, otherwise simple regex fallback
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        # remove scripts/styles
        for s in soup(["script", "style", "noscript"]):
            s.extract()
        paragraphs = soup.find_all("p")
        text = " ".join([p.get_text(separator=" ", strip=True) for p in paragraphs])
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception:
        # fallback: simple regex to take text between tags
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text

def split_into_sentences(text: str) -> List[str]:
    # very simple sentence splitter
    sents = re.split(r'(?<=[.!?])\s+', text.strip())
    sents = [s.strip() for s in sents if len(s.strip()) > 10]
    return sents

# -----------------------
# Mock "LLM" utilities
# -----------------------
STOPWORDS = set([
    "the","and","is","in","to","of","a","for","on","that","with","as","are","was","be",
    "it","by","an","from","at","this","which","or","have","has","but","not","they","their",
    "we","will","can","also","its","such","these","been","more","may"
])

def summarize_mock(text: str, max_sentences: int = 3) -> str:
    sents = split_into_sentences(text)
    if not sents:
        return "(ไม่พบข้อความที่จะสรุป)"
    # Simple extractive summary: pick first N sensible sentences
    return " ".join(sents[:max_sentences])

def extract_keywords_mock(text: str, top_k: int = 8) -> List[str]:
    # crude tokenization and frequency
    words = re.findall(r"\b[a-zA-Z']{3,}\b", text.lower())
    words = [w for w in words if w not in STOPWORDS]
    freq = Counter(words)
    common = [w for w, _ in freq.most_common(top_k)]
    return common

def make_vocab_entries(words: List[str]) -> List[Dict]:
    # create mock meanings and example sentences
    entries = []
    for w in words:
        meaning = f"Mock meaning of '{w}' (a short definition)."
        example = f"Example sentence using {w} in context."
        entries.append({"word": w, "meaning": meaning, "example": example})
    return entries

def generate_questions_mock(text: str, n_questions: int = 5) -> List[Dict]:
    # generate simple comprehension questions (mock)
    sents = split_into_sentences(text)
    questions = []
    # Q1: main idea
    if sents:
        questions.append({"q": "What is the main idea of the article?", "answer_hint": sents[0][:200]})
    # detail questions from later sentences
    for i in range(1, min(len(sents), n_questions)):
        q = f"What is one detail mentioned in sentence {i+1}?"
        questions.append({"q": q, "answer_hint": sents[i][:200]})
    # if not enough, create vocab-in-context questions
    keywords = extract_keywords_mock(text, top_k=5)
    for k in keywords[:max(0, n_questions - len(questions))]:
        questions.append({"q": f"What does '{k}' most likely mean in the article?", "answer_hint": f"Look for usage of '{k}' in the passage."})
    return questions[:n_questions]

# -----------------------
# Session state setup
# -----------------------
if "article_text" not in st.session_state:
    st.session_state.article_text = ""  # store as string
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "vocab_list" not in st.session_state:
    st.session_state.vocab_list = []  # list of dicts: {word, meaning, example}
if "questions" not in st.session_state:
    st.session_state.questions = []  # list of dicts: {q, answer_hint}
if "answers" not in st.session_state:
    st.session_state.answers = []  # user answers

# -----------------------
# UI: input area
# -----------------------
st.sidebar.header("การตั้งค่า")
st.sidebar.markdown("เวอร์ชันนี้เป็น *mock* — ถ้าต้องการความแม่นยำจริง ให้เชื่อม LLM API")

url = st.text_input("วาง URL ของบทความภาษาอังกฤษที่ต้องการสรุปที่นี่")

col_fetch, col_clear = st.columns([1, 1])
with col_fetch:
    if st.button("ดึงบทความจาก URL", key="btn_fetch"):
        if not url.strip():
            st.error("กรุณาวาง URL ก่อนกดปุ่ม")
        else:
            html = fetch_html(url.strip())
            if not html:
                st.error("ไม่สามารถโหลดหน้าเว็บได้ ลองตรวจสอบ URL หรือเชื่อมต่ออินเทอร์เน็ต")
            else:
                text = extract_text_from_html(html)
                if not text:
                    st.error("ไม่พบเนื้อหาบทความจากหน้าเว็บนี้")
                else:
                    st.session_state.article_text = text
                    st.success("ดึงบทความเรียบร้อยแล้ว")
with col_clear:
    if st.button("ล้างข้อมูลทั้งหมด", key="btn_clear"):
        st.session_state.article_text = ""
        st.session_state.summary = ""
        st.session_state.vocab_list = []
        st.session_state.questions = []
        st.session_state.answers = []
        st.success("ล้างข้อมูลแล้ว")

st.markdown("---")

# -----------------------
# Show article (preview)
# -----------------------
if st.session_state.article_text:
    st.subheader("📄 ตัวอย่างบทความ (ตัวอย่าง 1500 ตัวอักษรแรก)")
    st.write(st.session_state.article_text[:1500] + ("..." if len(st.session_state.article_text) > 1500 else ""))

    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if st.button("สรุปบทความ (สรุปแบบย่อ)", key="btn_summarize"):
            st.session_state.summary = summarize_mock(st.session_state.article_text)
            st.success("สรุปบทความเสร็จแล้ว")
    with col2:
        if st.button("ดึงคำศัพท์สำคัญจากบทความ", key="btn_vocab"):
            keywords = extract_keywords_mock(st.session_state.article_text, top_k=12)
            st.session_state.vocab_list = make_vocab_entries(keywords)
            st.success("ดึงคำศัพท์สำคัญเรียบร้อยแล้ว")
    with col3:
        if st.button("สร้างแบบทดสอบจับใจความ (ภาษาอังกฤษ)", key="btn_questions"):
            st.session_state.questions = generate_questions_mock(st.session_state.article_text, n_questions=5)
            # reset answers
            st.session_state.answers = [""] * len(st.session_state.questions)
            st.success("สร้างคำถามเรียบร้อยแล้ว")

# -----------------------
# Show summary & vocab table
# -----------------------
if st.session_state.summary:
    st.subheader("📝 สรุปบทความ (แบบย่อ)")
    st.write(st.session_state.summary)

if st.session_state.vocab_list:
    st.subheader("📚 ตารางคำศัพท์สำคัญ")
    # build dataframe temporarily from session_state list (do not store DF in session)
    df_vocab = pd.DataFrame(st.session_state.vocab_list)
    # show table with Thai headers
    df_show = df_vocab.rename(columns={"word":"คำศัพท์","meaning":"ความหมาย","example":"ประโยคตัวอย่าง"})
    st.dataframe(df_show)
    # download CSV
    csv_buf = df_vocab.to_csv(index=False)
    st.download_button("ดาวน์โหลดตารางคำศัพท์ (CSV)", csv_buf, file_name="vocabulary.csv")

# -----------------------
# Quiz / Test UI
# -----------------------
if st.session_state.questions:
    st.subheader("🧪 แบบทดสอบจับใจความ (ตอบเป็นภาษาอังกฤษ)")
    st.write("ตอบคำถามด้านล่างเป็นภาษาอังกฤษ แล้วกด 'ตรวจคำตอบ' เพื่อให้ระบบให้คะแนนแบบคร่าว ๆ (mock grading)")
    form = st.form(key="quiz_form")
    user_answers = []
    for i, q in enumerate(st.session_state.questions):
        form.write(f"**Q{i+1}. {q['q']}**")
        # prefill with existing if any
        existing = st.session_state.answers[i] if i < len(st.session_state.answers) else ""
        ans = form.text_area(f"Your answer for Q{i+1}", value=existing, key=f"ans_{i}")
        user_answers.append(ans)
        form.markdown("---")
    submitted = form.form_submit_button("ส่งคำตอบและตรวจคำตอบ")
    if submitted:
        # save answers
        st.session_state.answers = user_answers
        # grading (very simple mock): check overlap of important words from hint
        scores = []
        for ans, q in zip(user_answers, st.session_state.questions):
            hint_words = set(re.findall(r"\b[a-zA-Z']{4,}\b", q.get("answer_hint","").lower()))
            ans_words = set(re.findall(r"\b[a-zA-Z']{4,}\b", ans.lower()))
            if not hint_words:
                score = 1 if len(ans.strip())>10 else 0
            else:
                overlap = len(hint_words & ans_words)
                score = 1 if overlap >= max(1, len(hint_words)//4) else 0
            scores.append(score)
        total = sum(scores)
        st.success(f"คุณได้ {total} จาก {len(scores)} คะแนน (ระบบให้คะแนนแบบคร่าว ๆ)")
        # show per-question feedback
        for i, s in enumerate(scores):
            st.write(f"Q{i+1}: {'ถูกต้อง (ตามเงื่อนไขของระบบ)' if s>0 else 'ยังไม่ผ่าน - ลองตอบใหม่'}")
            st.caption(f"อ้างอิง hint: {st.session_state.questions[i]['answer_hint'][:200]}")

st.markdown("---")
st.caption("เวอร์ชัน Mock — หากต้องการให้สรุป/ดึงคำศัพท์/สร้างข้อสอบแม่นยำขึ้น ให้บอกฉันจะผนวก LLM API ให้ (OpenAI / Google Gemini ฯลฯ).")

