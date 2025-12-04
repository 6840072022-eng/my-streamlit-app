import os
import io
import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
import google.generativeai as genai  # ตามที่คุณต้องการให้ใช้

# ---------------------------
# Helpers: extract article text
# ---------------------------
def fetch_article_text(url):
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as e:
        return None, f"Error fetching URL: {e}"

    soup = BeautifulSoup(resp.text, "html.parser")

    # พยายามดึง article text ที่พบบ่อย
    article_tags = soup.find_all(['article'])
    if article_tags:
        texts = " ".join(t.get_text(separator=" ", strip=True) for t in article_tags)
    else:
        # fallback: รวม <p> ที่เห็น
        paragraphs = soup.find_all('p')
        texts = " ".join(p.get_text(separator=" ", strip=True) for p in paragraphs)

    # ตัดสั้นถ้าจำเป็น
    texts = " ".join(texts.split())
    return texts if texts.strip() else None, None

# ---------------------------
# Helpers: call Gemini via genai
# ---------------------------
def configure_genai(api_key):
    # ตั้งค่า key สำหรับไลบรารี
    genai.configure(api_key=api_key)
    # บางรุ่น/เวอร์ชันอาจใช้ client interface:
    try:
        client = genai.Client()  # ตามตัวอย่าง quickstart วิธีนี้ใช้ได้ในหลายเวอร์ชัน.  [oai_citation:1‡Google AI for Developers](https://ai.google.dev/gemini-api/docs/quickstart?utm_source=chatgpt.com)
    except Exception:
        client = None
    return client

def genai_generate_text(client, model_id, prompt, max_output_tokens=512):
    """
    ใช้งานฟังก์ชัน generate content ผ่าน client (preferred) หรือผ่าน GenerativeModel
    คืนค่า: text (string)
    """
    # ถ้ามี client ใช้ client.models.generate_content (quickstart pattern).  [oai_citation:2‡Google AI for Developers](https://ai.google.dev/gemini-api/docs/quickstart?utm_source=chatgpt.com)
    try:
        if client is not None:
            resp = client.models.generate_content(model=model_id, contents=prompt)
            # บางเวอร์ชันจะมี resp.text หรือ resp.outputs[0].content
            text = getattr(resp, "text", None) or (resp.outputs[0].content if getattr(resp, "outputs", None) else None)
            return text
    except Exception:
        pass

    # fallback: บางไลบรารีใช้ GenerativeModel
    try:
        model = genai.GenerativeModel(model_id)
        resp = model.generate_content(prompt)
        return getattr(resp, "text", None) or resp
    except Exception as e:
        return f"[Error calling genai] {e}"

# ---------------------------
# Prompt templates for tasks
# ---------------------------
PROMPTS = {
    "translate_th_to_fr_with_glossary": lambda text, params: (
        f"Task: แปลประโยค/ข้อความต่อไปนี้จากภาษาไทยเป็นภาษาฝรั่งเศส\n"
        f"ข้อกำหนด:\n"
        f"1) ให้ส่งออกเป็นตาราง 3 คอลัมน์ (คำศัพท์ภาษาไทย | คำแปลฝรั่งเศสแบบคำศัพท์ | ตัวอย่างประโยคที่ใช้คำศัพท์นั้น)\n"
        f"2) ถ้ามีคำเฉพาะหรือคำเทคนิค ให้ใส่คำอธิบายสั้น ๆ ด้วย\n\n"
        f"Input:\n{text}\n\n"
        f"Return: ตอบเป็น JSON list of objects หรือ markdown table."
    ),
    "generate_cloze_from_passage": lambda text, params: (
        f"Task: สร้างข้อสอบแบบ cloze test จำนวน {params.get('n',10)} ข้อจาก passage นี้\n"
        f"ข้อกำหนด:\n"
        f"- แต่ละข้อให้แสดง passage ย่อที่มีช่องว่าง (___) และตัวเลือก (ถ้าต้องการ) และคำตอบ\n"
        f"- ให้เลือกคำที่สำคัญหรือคำที่วัดความเข้าใจ\n\nPassage:\n{text}"
    ),
    "summarize_english_url": lambda text, params: (
        f"Task: สรุปข่าวภาษาอังกฤษให้สั้นและเข้าใจง่ายสำหรับระดับมัธยม\n"
        f"ข้อกำหนด:\n"
        f"- ความยาว summary ประมาณ {params.get('sentences',3)} ประโยค\n"
        f"- เลือกคำศัพท์ที่สำคัญและให้คำอธิบายสั้น ๆ สำหรับคำศัพท์ที่นักเรียนควรรู้\n\nArticle:\n{text}"
    ),
    "slogan_ideas_from_product": lambda text, params: (
        f"Task: อ่าน product description / branding ต่อไปนี้ แล้วสร้างสโลแกนสินค้า 20 ไอเดีย\n"
        f"ข้อกำหนด:\n"
        f"- แต่ละไอเดีย 1 บรรทัด\n"
        f"- เพิ่ม column แนะนำว่าควรใช้กับช่องทางการตลาดใด (เช่น Facebook, Instagram, Packaging)\n\nProduct description / branding:\n{text}"
    ),
    "vocab_list_with_pos_and_translation": lambda text, params: (
        f"Task: สกัดคำศัพท์จาก passage ต่อไปนี้ แล้วจัดเป็นตาราง (word | POS | คำแปลไทย | level) เรียงจากคำที่สำคัญ/ยากไปหาง่าย\n"
        f"ข้อกำหนด:\n"
        f"- จำกัดผลลัพธ์ไม่เกิน {params.get('limit',50)} คำ\n\nPassage:\n{text}"
    ),
}

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(layout="wide", page_title="NLP LLM App (Gemini)")

st.title("NLP application - Gemini (Streamlit)")

# Sidebar: API key และการตั้งค่า
st.sidebar.header("API settings")
api_key = st.sidebar.text_input("ใส่ Google Gemini API Key (จาก Google AI Studio)", type="password")
model_choice = st.sidebar.selectbox("เลือก model (suggested)", ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.0"])
max_tokens = st.sidebar.slider("Max tokens (output limit)", min_value=128, max_value=2048, value=512, step=64)

if not api_key:
    st.sidebar.info("กรุณาใส่ API key ในช่องด้านบนเพื่อให้เรียกใช้งาน Gemini ได้")
client = None
if api_key:
    client = configure_genai(api_key)

# Main: input options (URL หรือ upload)
st.subheader("Input: ดึงบทความจาก URL หรืออัพโหลดไฟล์ CSV/Excel (มี column ที่มี text)")
input_mode = st.radio("", ["URL", "Upload file", "Paste text"])

article_text = ""
error_msg = None

if input_mode == "URL":
    url = st.text_input("ใส่ URL ของบทความ (http(s)://...)")
    if st.button("Fetch article"):
        if not url:
            st.warning("กรุณาใส่ URL")
        else:
            text, err = fetch_article_text(url)
            if err:
                st.error(err)
            elif not text:
                st.error("ไม่พบเนื้อหาจากหน้าเว็บนั้น ๆ")
            else:
                article_text = text
                st.success("ดึงบทความเรียบร้อย (แสดงตัวอย่างด้านล่าง)")
                st.text_area("Article text (preview)", article_text[:2000], height=250)
elif input_mode == "Upload file":
    uploaded = st.file_uploader("อัพโหลด CSV หรือ Excel", type=["csv", "xlsx"])
    if uploaded is not None:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            st.dataframe(df.head())
            # ให้ผู้ใช้เลือกคอลัมน์ที่ต้องการนำเข้าเป็น text
            text_col = st.selectbox("เลือก column ที่เป็นข้อความสำหรับประมวลผล", df.columns)
            # ผู้ใช้เลือกแถวที่ต้องการประมวลผล (หรือทั้งไฟล์)
            process_rows = st.multiselect("เลือก index rows (ว่าง=ทั้งหมด)", df.index.tolist())
            if st.button("ใช้ไฟล์นี้เป็น input"):
                if len(process_rows) == 0:
                    selected_texts = df[text_col].astype(str).tolist()
                else:
                    selected_texts = df.loc[process_rows, text_col].astype(str).tolist()
                article_text = "\n\n".join(selected_texts)
                st.success("นำข้อมูลเข้าเรียบร้อย")
        except Exception as e:
            st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")
else:
    article_text = st.text_area("วางข้อความที่ต้องการประมวลผลที่นี่", height=250)

# Task selection
st.subheader("เลือกงาน (Task)")
task = st.selectbox("Task", [
    ("Translate Thai -> French with glossary", "translate_th_to_fr_with_glossary"),
    ("Generate cloze test (from passage)", "generate_cloze_from_passage"),
    ("Summarize English article (URL)", "summarize_english_url"),
    ("Generate product slogan ideas", "slogan_ideas_from_product"),
    ("Extract vocab list (with POS & translation)", "vocab_list_with_pos_and_translation"),
], format_func=lambda x: x[0])[1]

# Task-specific params
params = {}
if task == "generate_cloze_from_passage":
    params['n'] = st.number_input("จำนวนข้อ (n)", min_value=1, max_value=50, value=10)
elif task == "summarize_english_url":
    params['sentences'] = st.number_input("จำนวนประโยคในสรุป", min_value=1, max_value=10, value=3)
elif task == "vocab_list_with_pos_and_translation":
    params['limit'] = st.number_input("จำกัดจำนวนคำ", min_value=5, max_value=200, value=50)

# Run
st.markdown("---")
if st.button("Run Task"):
    if not api_key:
        st.error("ต้องใส่ API key ใน sidebar ก่อน")
    elif not article_text or len(article_text.strip()) < 20:
        st.error("กรุณาเตรียม input (URL / file / paste text) ให้เรียบร้อยก่อน")
    else:
        st.info("เรียกใช้งาน LLM กำลังประมวลผล...")
        prompt = PROMPTS[task](article_text, params)
        model_id = model_choice
        result_text = genai_generate_text(client, model_id, prompt, max_output_tokens=max_tokens)

        # ถ้าได้ผลลัพธ์เป็น JSON-like หรือ table ให้พยายามแปลงเป็น DataFrame
        df_out = None
        try:
            # พยายาม parse เป็น JSON ถ้าเป็นไปได้
            import json
            j = json.loads(result_text)
            if isinstance(j, list):
                df_out = pd.DataFrame(j)
            elif isinstance(j, dict):
                df_out = pd.DataFrame([j])
        except Exception:
            pass

        # ถ้าไม่ parse เป็น JSON ให้ลองแปลงจาก markdown table (simple)
        if df_out is None:
            # พยายามแปลงบรรทัดที่เป็น " | " เป็นตาราง
            lines = [l for l in (result_text or "").splitlines() if l.strip()]
            table_lines = [l for l in lines if "|" in l]
            if table_lines:
                try:
                    df_out = pd.read_csv(io.StringIO("\n".join(table_lines)), sep="|", engine="python", header=None)
                    # cleanup: strip whitespace
                    df_out = df_out.applymap(lambda x: x.strip() if isinstance(x, str) else x)
                except Exception:
                    df_out = None

        # แสดงผล
        if df_out is not None:
            st.success("ได้ผลลัพธ์เป็นตาราง (DataFrame)")
            st.dataframe(df_out)
            # ให้ดาวน์โหลด
            csv_bytes = df_out.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv_bytes, file_name="result.csv", mime="text/csv")
        else:
            st.success("ได้ผลลัพธ์ข้อความจากโมเดล")
            st.text_area("Model output", result_text, height=400)
            # ถ้าอยากเซฟเป็นไฟล์ txt ให้ดาวน์โหลด
            st.download_button("Download result (txt)", result_text, file_name="result.txt", mime="text/plain")

        st.balloons()

# Footer: note about SDK usage
st.markdown("#### หมายเหตุ")
st.markdown("- โค้ดตัวอย่างนี้ใช้ `google.generativeai` / client interface ในการเรียก Gemini. วิธีการเรียกและชื่อ model อาจเปลี่ยนได้ตามเวอร์ชัน SDK/นโยบายของ Google — หากเจอ error ให้ตรวจสอบเอกสาร SDK หรือเวอร์ชันของไลบรารี.  [oai_citation:3‡Google AI for Developers](https://ai.google.dev/gemini-api/docs/quickstart?utm_source=chatgpt.com)")
