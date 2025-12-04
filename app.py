
# app.py — All-in-one Reading Assistant (OpenAI + Google Gemini REST)
# Requirements (example): streamlit, pandas, requests, beautifulsoup4, openai
# Put requirements.txt in same folder as app.py before deploy.

import streamlit as st
import pandas as pd
import requests
import json
import re
import io
from collections import Counter
from typing import List, Dict
from bs4 import BeautifulSoup
import openai
import time

# -------------------------
# Page config & title
# -------------------------
st.set_page_config(page_title="Reading Assistant — TOEIC/IELTS/Arts English", layout="wide")
st.title("📘 Practicing Reading Skill from a Passage")
st.caption("For learners preparing for TOEIC or IELTS tests, as well as English I & II for Arts students.  ยกตัวอย่างเช่น บทความจาก BBC, Medium, The Guardian เป็นต้น")

# -------------------------
# Sidebar: API settings
# -------------------------
st.sidebar.header("🔑 API Configuration")
api_provider = st.sidebar.selectbox("เลือก LLM ที่ต้องการใช้", ["OpenAI", "Google Gemini (REST)"])

openai_key_input = ""
gemini_key_input = ""
if api_provider == "OpenAI":
    openai_key_input = st.sidebar.text_input("ใส่ OpenAI API Key", type="password")
else:
    gemini_key_input = st.sidebar.text_input("ใส่ Google API Key for Generative Language (REST)", type="password")

# OpenAI config helper
def call_openai_chat(prompt: str, model: str = "gpt-4o-mini", max_tokens: int = 600) -> str:
    if not openai_key_input:
        return "⚠️ กรุณาใส่ OpenAI API Key ใน sidebar"
    openai.api_key = openai_key_input
    try:
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "system", "content": "You are a helpful assistant that summarizes articles, extracts vocabulary, and generates reading comprehension questions in clean JSON when requested."},
                      {"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message["content"].strip()
    except Exception as e:
        return f"❌ OpenAI error: {e}"

# Google Gemini REST helper
def call_gemini_rest(prompt: str, model: str = "gemini-1.5-pro") -> str:
    if not gemini_key_input:
        return "⚠️ กรุณาใส่ Google API Key ใน sidebar"
    # Endpoint: model:generateContent
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key_input}"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    payload = {
        "contents": [
            {
                "mimeType": "text/plain",
                "parts": [{"text": prompt}]
            }
        ],
        # You can tune temperature / candidate_count etc if needed
        "temperature": 0.1,
        "candidateCount": 1,
        "maxOutputTokens": 800
    }
    try:
        r = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        if r.status_code != 200:
            return f"❌ Gemini API error {r.status_code}: {r.text}"
        data = r.json()
        # parse expected path
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            # Some endpoints use "candidates" under top-level "candidates"
            if "candidates" in data and isinstance(data["candidates"], list):
                return json.dumps(data)
            return f"⚠️ Unexpected Gemini response: {json.dumps(data)[:400]}"
    except Exception as e:
        return f"❌ Gemini request error: {e}"

# Generic ask_llm
def ask_llm(prompt: str, provider: str):
    if provider == "OpenAI":
        return call_openai_chat(prompt)
    else:
        return call_gemini_rest(prompt)

# -------------------------
# HTML fetch / extract
# -------------------------
def fetch_html(url: str, timeout: int = 10) -> str:
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        return ""

def extract_text_from_html(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        paragraphs = soup.find_all("p")
        text = " ".join([p.get_text(separator=" ", strip=True) for p in paragraphs])
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception:
        text = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", text).strip()

def split_into_sentences(text: str) -> List[str]:
    sents = re.split(r'(?<=[.!?])\s+', text.strip())
    sents = [s.strip() for s in sents if len(s.strip()) > 10]
    return sents

# -------------------------
# LLM Prompted tasks (produce JSON)
# -------------------------
def prompt_summarize_json(article_text: str) -> str:
    prompt = (
        "Please produce a concise English summary (3-5 sentences) of the following article. "
        "Return only the summary text (no numbering). Article:\n\n" + article_text
    )
    return prompt

def prompt_extract_vocab_json(article_text: str, n_words: int = 12) -> str:
    # Request JSON array of objects: word, pos, meaning, example, cefr
    prompt = (
        f"Extract the top {n_words} most important vocabulary words from the article below. "
        "For each word, provide JSON object with fields: 'word' (lowercase), 'pos' (noun/verb/adj/adv/other), "
        "'meaning' (simple English definition), 'example' (one natural example sentence extracted or inspired by the article), "
        "'cefr' (one of A1,A2,B1,B2,C1,C2). Return a JSON array only. Article:\n\n" + article_text
    )
    return prompt

def prompt_generate_questions_json(article_text: str, n_questions: int = 7) -> str:
    # return JSON array; each item: {type: "mcq"/"cloze"/"short", q, choices:[..] OR blank, answer, explanation}
    prompt = (
        f"Create {n_questions} reading-comprehension questions (mix of multiple-choice and cloze and short-answer) "
        "from the article. For each question return a JSON object with keys: 'type' (mcq/cloze/short), 'q' (question text), "
        "'choices' (array of 4 choices for mcq; for cloze/short use empty array), 'answer' (correct answer), 'explanation' (brief explanation). "
        "Make distractors plausible. Return a JSON array only. Article:\n\n" + article_text
    )
    return prompt

# -------------------------
# Utility: parse JSON safely from LLM text
# -------------------------
def extract_json_from_text(text: str):
    """
    Tries to find the first JSON array/object in text and parse it.
    Returns python object or None.
    """
    if not text:
        return None
    # Try to locate first { or [
    start = None
    for i, ch in enumerate(text):
        if ch in ('[', '{'):
            start = i
            break
    if start is None:
        # maybe the model returned pure JSON-like but prefixed; try json.loads direct
        try:
            return json.loads(text)
        except Exception:
            return None
    # try to find matching end by naive approach: try progressively larger substrings
    for end in range(len(text), start, -1):
        candidate = text[start:end]
        try:
            return json.loads(candidate)
        except Exception:
            continue
    # final fallback
    try:
        return json.loads(text)
    except Exception:
        return None

# -------------------------
# Session state init
# -------------------------
if "article_text" not in st.session_state:
    st.session_state.article_text = ""
if "summary_text" not in st.session_state:
    st.session_state.summary_text = ""
if "vocab_list" not in st.session_state:
    st.session_state.vocab_list = []  # list of dicts
if "questions_list" not in st.session_state:
    st.session_state.questions_list = []  # list of dicts

# -------------------------
# Input area: URL or File
# -------------------------
st.subheader("📥 Input Article")
input_mode = st.radio("เลือกรูปแบบการนำเข้าข้อมูล", ["URL", "Upload CSV/Excel"], horizontal=True)

col1, col2 = st.columns([3,1])
with col1:
    if input_mode == "URL":
        url = st.text_input("วาง URL ของบทความภาษาอังกฤษที่ต้องการสรุปที่นี่ (เช่น BBC, Medium, The Guardian)")
    else:
        uploaded_file = st.file_uploader("อัปโหลดไฟล์ CSV หรือ Excel (คอลัมน์ข้อความ/paragraphs)", type=["csv","xlsx","xls"])

with col2:
    if st.button("ล้างข้อมูลทั้งหมด"):
        st.session_state.article_text = ""
        st.session_state.summary_text = ""
        st.session_state.vocab_list = []
        st.session_state.questions_list = []
        st.success("ล้างข้อมูลเรียบร้อย")

# Load content
if input_mode == "URL":
    if st.button("ดึงบทความจาก URL"):
        if not url or not url.strip():
            st.error("กรุณาใส่ URL ก่อนกดปุ่ม")
        else:
            html = fetch_html(url.strip())
            if not html:
                st.error("ไม่สามารถโหลดหน้าเว็บได้")
            else:
                text = extract_text_from_html(html)
                if not text:
                    st.error("ไม่พบเนื้อหาจากหน้าเว็บนี้")
                else:
                    st.session_state.article_text = text
                    st.success("ดึงบทความสำเร็จ")
else:
    if uploaded_file is not None:
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                df_in = pd.read_csv(uploaded_file)
            else:
                df_in = pd.read_excel(uploaded_file)
            # combine all text columns into single passage
            text = " ".join(df_in.astype(str).stack().tolist())
            st.session_state.article_text = text
            st.success("โหลดไฟล์สำเร็จ")
            st.dataframe(df_in.head(20))
        except Exception as e:
            st.error(f"อ่านไฟล์ล้มเหลว: {e}")

st.markdown("---")

# -------------------------
# Action buttons: Summarize / Vocab / Questions
# -------------------------
if st.session_state.article_text:
    st.subheader("📄 Article preview (first 1500 chars)")
    st.write(st.session_state.article_text[:1500] + ("..." if len(st.session_state.article_text) > 1500 else ""))

    col_a, col_b, col_c = st.columns([1,1,1])
    with col_a:
        if st.button("📝 สรุปบทความ (LLM)"):
            with st.spinner("กำลังสรุปโดย LLM ..."):
                prompt = prompt_summarize_json(st.session_state.article_text)
                resp_text = ask_llm(prompt, api_provider)
                # resp_text should be plain summary; store directly
                st.session_state.summary_text = resp_text
                st.success("สรุปเรียบร้อย")
    with col_b:
        if st.button("📚 วิเคราะห์คำศัพท์เชิงลึก (LLM)"):
            with st.spinner("กำลังดึงคำศัพท์โดย LLM ..."):
                prompt = prompt_extract_vocab_json(st.session_state.article_text, n_words=15)
                resp_text = ask_llm(prompt, api_provider)
                parsed = extract_json_from_text(resp_text)
                if parsed is None or not isinstance(parsed, list):
                    # fallback: try to request simpler format
                    st.warning("LLM ไม่ได้ส่ง JSON ตามที่คาดไว้ — จะแปลงผลแบบ fallback")
                    # simple fallback: extract frequent words
                    words = re.findall(r"\b[a-zA-Z']{4,}\b", st.session_state.article_text.lower())
                    freq = Counter(words)
                    top = [w for w,_ in freq.most_common(12)]
                    parsed = [{"word":w,"pos":"","meaning":"","example":"","cefr":""} for w in top]
                # normalize entries
                vocab_list = []
                for i, item in enumerate(parsed):
                    try:
                        w = item.get("word", "").strip()
                        pos = item.get("pos", "") if isinstance(item.get("pos",""), str) else ""
                        meaning = item.get("meaning", "")
                        example = item.get("example", "")
                        cefr = item.get("cefr", "")
                    except Exception:
                        continue
                    if w:
                        vocab_list.append({"word": w, "pos": pos, "meaning": meaning, "example": example, "cefr": cefr})
                st.session_state.vocab_list = vocab_list
                st.success(f"ดึงคำศัพท์ {len(vocab_list)} รายการเรียบร้อย")
    with col_c:
        if st.button("🧪 สร้างแบบทดสอบจับใจความ (LLM)"):
            with st.spinner("กำลังสร้างคำถามโดย LLM ..."):
                prompt = prompt_generate_questions_json(st.session_state.article_text, n_questions=8)
                resp_text = ask_llm(prompt, api_provider)
                parsed = extract_json_from_text(resp_text)
                if parsed is None or not isinstance(parsed, list):
                    st.warning("LLM ไม่ได้ส่ง JSON ตามที่คาดไว้ — สร้างคำถามแบบ fallback")
                    # fallback: simple questions from first sentences
                    sents = split_into_sentences(st.session_state.article_text)
                    parsed = []
                    for i in range(min(5, len(sents))):
                        parsed.append({"type":"short","q":f"What is the main idea of sentence {i+1}?","choices":[],"answer":"","explanation":sents[i][:200]})
                # normalize questions
                qlist = []
                for item in parsed:
                    qtype = item.get("type","short")
                    qtext = item.get("q","")
                    choices = item.get("choices",[]) if isinstance(item.get("choices",[]), list) else []
                    answer = item.get("answer","")
                    explanation = item.get("explanation","")
                    qlist.append({"type": qtype, "q": qtext, "choices": choices, "answer": answer, "explanation": explanation})
                st.session_state.questions_list = qlist
                st.success(f"สร้างคำถาม {len(qlist)} ข้อเรียบร้อย")

# -------------------------
# Show outputs: Summary, Vocab DataFrame, Questions DataFrame
# -------------------------
st.markdown("---")
if st.session_state.summary_text:
    st.subheader("📝 Summary")
    st.write(st.session_state.summary_text)

if st.session_state.vocab_list:
    st.subheader("📚 Vocabulary — Detailed")
    df_vocab = pd.DataFrame(st.session_state.vocab_list)
    # Ensure columns exist
    for col in ["word","pos","meaning","example","cefr"]:
        if col not in df_vocab.columns:
            df_vocab[col] = ""
    df_show = df_vocab.rename(columns={"word":"Word","pos":"POS","meaning":"Meaning","example":"Example","cefr":"CEFR"})
    # sort by CEFR (custom order) then alphabetically
    cefr_order = {"A1":0,"A2":1,"B1":2,"B2":3,"C1":4,"C2":5,"":999}
    df_show["CEFR_rank"] = df_show["CEFR"].map(lambda x: cefr_order.get(x.upper(), 999) if isinstance(x,str) else 999)
    df_show = df_show.sort_values(by=["CEFR_rank","Word"]).drop(columns=["CEFR_rank"])
    st.dataframe(df_show.reset_index(drop=True))
    # download
    csv_buf = df_vocab.to_csv(index=False)
    st.download_button("ดาวน์โหลดตารางคำศัพท์ (CSV)", csv_buf, file_name="vocabulary.csv")

if st.session_state.questions_list:
    st.subheader("🧾 Generated Questions")
    # normalize to DataFrame with columns: No, type, q, A,B,C,D, answer, explanation
    rows = []
    for i, q in enumerate(st.session_state.questions_list, start=1):
        r = {"No": i, "type": q.get("type","short"), "q": q.get("q",""), "A":"", "B":"","C":"","D":"", "answer": q.get("answer",""), "explanation": q.get("explanation","")}
        choices = q.get("choices",[])
        for idx, ch in enumerate(choices[:4]):
            r[chr(ord("A")+idx)] = ch
        rows.append(r)
    df_q = pd.DataFrame(rows)
    st.dataframe(df_q)
    csv_q = df_q.to_csv(index=False)
    st.download_button("ดาวน์โหลดแบบทดสอบ (CSV)", csv_q, file_name="questions.csv")

# -------------------------
# Optional: interactive quiz (user answers input + grading simple)
# -------------------------
if st.session_state.questions_list:
    st.markdown("---")
    st.subheader("📝 ลองทำแบบทดสอบ (ตอบเป็นภาษาอังกฤษ)")
    with st.form("quiz_form"):
        user_answers = []
        for i, q in enumerate(st.session_state.questions_list, start=1):
            st.markdown(f"**Q{i}. {q.get('q','')}**")
            if q.get("type") == "mcq" and q.get("choices"):
                choice = st.radio(f"เลือกคำตอบ Q{i}", options=q.get("choices"), key=f"rad_{i}")
                user_answers.append(choice)
            else:
                ans = st.text_area(f"คำตอบ Q{i}", key=f"text_{i}")
                user_answers.append(ans)
        submitted = st.form_submit_button("ส่งคำตอบเพื่อให้ระบบตรวจคร่าว ๆ")
        if submitted:
            # very simple auto-check for MCQ (exact match) and for short answers check overlap keywords
            score = 0
            max_score = len(st.session_state.questions_list)
            feedback = []
            for i, (q, uans) in enumerate(zip(st.session_state.questions_list, user_answers), start=1):
                correct = q.get("answer","")
                if q.get("type") == "mcq" and q.get("choices"):
                    ok = (str(uans).strip().lower() == str(correct).strip().lower())
                    if ok:
                        score += 1
                    feedback.append((i, ok, correct, q.get("explanation","")))
                else:
                    # short answer fuzzy: check shared keywords with explanation/hint
                    hint = q.get("explanation","")
                    hint_words = set(re.findall(r"\b[a-zA-Z']{4,}\b", hint.lower()))
                    ans_words = set(re.findall(r"\b[a-zA-Z']{4,}\b", str(uans).lower()))
                    overlap = len(hint_words & ans_words)
                    ok = overlap >= max(1, len(hint_words)//4) if hint_words else len(str(uans).strip())>20
                    if ok:
                        score += 1
                    feedback.append((i, ok, correct, q.get("explanation","")))
            st.success(f"คุณได้ {score} จาก {max_score} คะแนน (คะแนนประมาณการ)")
            for f in feedback:
                i, ok, corr, expl = f
                st.write(f"Q{i}: {'ถูก' if ok else 'ยังไม่ผ่าน'} — คำตอบที่ถูก: {corr}")
                st.caption(f"Explanation/hint: {expl[:250]}")

st.markdown("---")
st.caption("เวอร์ชัน: All-in-one Reading Assistant — ใช้ Google Gemini ผ่าน REST API หรือ OpenAI ได้. หากต้องการปรับ prompt ให้เข้มขึ้นหรือเปลี่ยน model/จำนวนคำศัพท์/จำนวนคำถาม บอกได้เลย.")

