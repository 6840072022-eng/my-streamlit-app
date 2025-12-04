import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import time
import base64
from urllib.parse import urlparse

# --- การตั้งค่าและตัวแปร ---

# กำหนด API Key เป็นสตริงว่างเปล่า
API_KEY = ""

# URL ของ Gemini API
GEMINI_API_URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key="

# --- ฟังก์ชันช่วยเหลือสำหรับการโต้ตอบกับ LLM ---

def llm_call_with_retry(payload, api_url, max_retries=3):
    """เรียกใช้ Gemini API พร้อมกลไกการลองใหม่แบบ Exponential Backoff"""
    
    # ดึง API Key จาก session state
    api_key = st.session_state.get('gemini_api_key', API_KEY)
    
    # ตรวจสอบว่ามี API Key หรือไม่
    if not api_key:
        # ฟังก์ชันนี้จะไม่ถูกเรียก ถ้า has_api_key เป็น False ใน main() 
        # แต่ใส่ไว้เพื่อความปลอดภัย
        st.error("❌ ไม่พบ Google Gemini API Key. ไม่สามารถเรียกใช้ LLM ได้")
        return None
        
    # สร้าง URL ที่สมบูรณ์
    full_api_url = f"{api_url}{api_key}"
    
    for attempt in range(max_retries):
        try:
            # ใช้ requests.post เพื่อจำลองการเรียก API
            response = requests.post(
                full_api_url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(payload)
            )
            response.raise_for_status() # ตรวจสอบข้อผิดพลาด HTTP

            result = response.json()
            
            # ตรวจสอบว่ามีเนื้อหาที่สร้างขึ้นมาหรือไม่
            if result.get('candidates') and result['candidates'][0].get('content'):
                return result
            else:
                # กรณีที่โมเดลตอบกลับมาแต่ไม่มีเนื้อหา (เช่น ถูกบล็อก)
                st.warning(f"Gemini API ไม่ได้สร้างเนื้อหา: {result.get('promptFeedback')}")
                return None

        except requests.exceptions.HTTPError as e:
            st.error(f"HTTP Error: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                st.error("การเรียก API ล้มเหลวหลังจากพยายามหลายครั้ง")
                return None
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            return None
    return None

def extract_content_from_url(url):
    """ดึงเนื้อหาที่เป็นข้อความจาก URL โดยใช้ BeautifulSoup"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # ลบองค์ประกอบที่ไม่จำเป็นออก เช่น script, style, header, footer, nav
        for selector in ['script', 'style', 'header', 'footer', 'nav', '.sidebar', '.ad', 'img']:
            for element in soup.find_all(selector):
                element.decompose()

        # พยายามดึงข้อความจากแท็ก <article> หรือแท็กหลักๆ
        article_body = soup.find('article') or soup.find('main') or soup.find('body')

        if not article_body:
            return None, "ไม่พบส่วนเนื้อหาหลักของบทความ"

        # รวบรวมข้อความจากย่อหน้าต่างๆ
        paragraphs = article_body.find_all('p')
        text_content = "\n".join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])

        # ดึงชื่อเรื่อง
        title = soup.find('title').get_text() if soup.find('title') else urlparse(url).netloc
        
        if not text_content:
             return None, "ไม่พบเนื้อหาที่เป็นข้อความในย่อหน้า"

        return text_content, title

    except requests.exceptions.RequestException as e:
        return None, f"ไม่สามารถเข้าถึง URL หรือเกิดข้อผิดพลาดในการเชื่อมต่อ: {e}"
    except Exception as e:
        return None, f"เกิดข้อผิดพลาดในการประมวลผลหน้าเว็บ: {e}"


def get_structured_data_llm(article_text, system_prompt, schema, task_name):
    """สร้างข้อมูลที่มีโครงสร้าง (JSON) จาก LLM"""
    
    # Prompt ที่รวมเนื้อหาบทความ
    user_prompt = f"ใช้บทความด้านล่างนี้เพื่อสร้างข้อมูลตามรูปแบบ JSON ที่กำหนด บทความ:\n\n---\n{article_text}\n---"
    
    payload = {
        "contents": [{"parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema
        },
    }

    with st.spinner(f"กำลังสร้าง {task_name} ด้วย Gemini API..."):
        result = llm_call_with_retry(payload, GEMINI_API_URL_BASE)

    if result:
        try:
            # ดึง JSON string และแปลงเป็น Python object
            json_string = result['candidates'][0]['content']['parts'][0]['text']
            data = json.loads(json_string)
            return pd.DataFrame(data)
        except (json.JSONDecodeError, KeyError) as e:
            st.error(f"เกิดข้อผิดพลาดในการถอดรหัส JSON จาก Gemini API สำหรับ {task_name}: {e}")
            st.code(result) # แสดงผลลัพธ์ดิบเพื่อการดีบัก
            return None
    return None

def get_summary_llm(article_text, system_prompt):
    """สร้างสรุปบทความจาก LLM (ข้อความธรรมดา)"""
    
    payload = {
        "contents": [{"parts": [{"text": article_text}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }

    with st.spinner("กำลังสรุปบทความด้วย Gemini API..."):
        result = llm_call_with_retry(payload, GEMINI_API_URL_BASE)

    if result and result['candidates'][0]['content']['parts'][0]['text']:
        return result['candidates'][0]['content']['parts'][0]['text']
    return "ไม่สามารถสร้างสรุปบทความได้"

# --- ฟังก์ชันสำหรับสร้าง DataFrames และ Schema ---

def create_vocab_schema():
    """กำหนด Schema สำหรับการดึงคำศัพท์"""
    return {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "word": {"type": "STRING", "description": "คำศัพท์ภาษาเดิม"},
                "translation": {"type": "STRING", "description": "คำแปลเป็นภาษาไทย"},
                "partOfSpeech": {"type": "STRING", "description": "ชนิดของคำ (เช่น Noun, Verb, Adjective)"},
                "difficulty": {"type": "STRING", "description": "ระดับความยาก (เช่น Easy, Medium, Hard)"},
                "exampleSentence": {"type": "STRING", "description": "ประโยคตัวอย่างการใช้คำนั้น"},
            },
            "propertyOrdering": ["word", "translation", "partOfSpeech", "difficulty", "exampleSentence"]
        }
    }

def create_question_schema():
    """กำหนด Schema สำหรับการสร้างโจทย์"""
    return {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "questionNumber": {"type": "INTEGER", "description": "ลำดับข้อคำถาม"},
                "sentenceWithBlank": {"type": "STRING", "description": "ประโยคเติมคำที่หายไป (Cloze Test) โดยแทนคำที่หายไปด้วย '____'"},
                "correctAnswer": {"type": "STRING", "description": "คำตอบที่ถูกต้อง"},
                "explanation": {"type": "STRING", "description": "คำอธิบายว่าทำไมคำตอบนี้จึงถูกต้อง (ภาษาไทย)"},
            },
            "propertyOrdering": ["questionNumber", "sentenceWithBlank", "correctAnswer", "explanation"]
        }
    }

# --- ฟังก์ชันสำหรับดาวน์โหลด DataFrame ---

def dataframe_to_csv_download_link(df, filename="result.csv", link_text="ดาวน์โหลดเป็น CSV"):
    """สร้างลิงก์สำหรับดาวน์โหลด DataFrame เป็นไฟล์ CSV"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}" class="stDownloadButton">{link_text}</a>'
    st.markdown(href, unsafe_allow_html=True)

# --- Streamlit UI หลัก ---

def main():
    st.set_page_config(layout="wide", page_title="เครื่องมือช่วยอ่านด้วย LLM")
    
    st.markdown("""
        <style>
            .stApp { background-color: #f0f2f6; }
            .stDownloadButton > a {
                display: inline-flex; align-items: center; justify-content: center; 
                padding: 0.25rem 0.75rem; border-radius: 0.5rem; color: white;
                background-color: #4CAF50; border: 1px solid #4CAF50;
                text-decoration: none; font-weight: 600; transition: background-color 0.2s;
            }
            .stDownloadButton > a:hover { background-color: #45a049; }
            h1 { color: #333; }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("📚 เครื่องมือช่วยอ่านและวิเคราะห์บทความด้วย LLM")
    st.subheader("วิเคราะห์ข้อมูลจาก URL หรือไฟล์ CSV/Excel")

    # --- Sidebar สำหรับ API Key และการตั้งค่า ---
    with st.sidebar:
        st.header("การตั้งค่า API (Optional)")
        
        # ใช้ st.text_input เพื่อรับ API Key
        api_key_input = st.text_input(
            "Google Gemini API Key (ถ้ามี)",
            type="password",
            value=st.session_state.get('gemini_api_key', '')
        )
        
        # บันทึกหรือลบ API Key ใน session state
        if api_key_input:
            st.session_state['gemini_api_key'] = api_key_input
            st.success("✅ API Key บันทึกแล้ว")
        elif 'gemini_api_key' in st.session_state:
            del st.session_state['gemini_api_key']
            st.info("ไม่พบ API Key - ฟังก์ชัน LLM (คำศัพท์/โจทย์/สรุป) จะถูกปิด")
            
        st.markdown("---")
        st.header("คำแนะนำ")
        st.markdown("""
        * **Input หลัก:** เลือกได้ระหว่าง **URL** หรือ **ไฟล์**
        * **ฟังก์ชันเสริม (LLM):** จะทำงานก็ต่อเมื่อมีการกรอก **Gemini API Key** เท่านั้น
        * **ถ้าใส่ API Key:** จะสร้างลิสต์คำศัพท์, โจทย์, และสรุปจาก **URL**
        * **ถ้าไม่ใส่ API Key:** จะทำได้แค่การดึงเนื้อหาจาก URL หรือแสดงข้อมูลจากไฟล์ที่อัปโหลด
        """)
        
    # ตรวจสอบ API Key
    has_api_key = 'gemini_api_key' in st.session_state and st.session_state['gemini_api_key']

    # --- Input หลัก: URL หรือ File ---
    st.markdown("## 📥 เลือกแหล่งข้อมูล")
    
    tab1, tab2 = st.tabs(["🌎 วิเคราะห์จาก URL", "📁 อัปโหลดไฟล์ CSV/Excel"])
    
    article_text = None
    title = ""

    with tab1:
        st.markdown("#### 🔗 วิเคราะห์เนื้อหาจากหน้าเว็บ")
        article_url = st.text_input(
            "กรุณาป้อน URL ของบทความ:",
            "https://en.wikipedia.org/wiki/Large_language_model"
        )
        if st.button("🚀 ดึงเนื้อหาจาก URL", key="analyze_url", type="primary"):
            # 1. ดึงเนื้อหาบทความ
            with st.status("กำลังดึงเนื้อหาจาก URL...", expanded=True) as status:
                article_text, title = extract_content_from_url(article_url)
                
                if article_text is None:
                    st.error(f"ไม่สามารถดำเนินการต่อได้: {title}")
                    status.update(label="การดึงเนื้อหาล้มเหลว", state="error", expanded=False)
                    return
                
                st.success(f"ดึงเนื้อหาสำเร็จ! ชื่อเรื่อง: {title}")
                
                # แสดงเนื้อหาที่ดึงมา
                st.markdown("#### เนื้อหาบทความที่ดึงมา")
                st.caption(f"Source URL: {article_url}")
                st.code(article_text[:1000] + "..." if len(article_text) > 1000 else article_text, language='text')

                status.update(label="ดึงเนื้อหาสำเร็จ", state="complete", expanded=False)

    with tab2:
        st.markdown("#### 📂 วิเคราะห์ข้อมูลจากตาราง")
        uploaded_file = st.file_uploader("เลือกไฟล์ CSV หรือ Excel เพื่อแสดงข้อมูล", type=["csv", "xlsx"])

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    data_df = pd.read_csv(uploaded_file)
                else:
                    data_df = pd.read_excel(uploaded_file)
                
                st.success("อัปโหลดไฟล์สำเร็จ! แสดงข้อมูลตัวอย่าง:")
                st.dataframe(data_df, use_container_width=True)
                
                # NOTE: ถ้าต้องการวิเคราะห์ข้อมูลในตารางนี้ด้วย LLM ต้องเพิ่ม logic 
                # และ prompt ที่เหมาะสมในส่วนนี้
                if has_api_key:
                    st.info("⚠️ **TODO:** หากคุณต้องการให้ LLM วิเคราะห์ข้อมูลตารางนี้, กรุณาเพิ่ม logic ในการเรียก LLM พร้อม Prompt และ Schema ที่เหมาะสม.")
                
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")
                
    st.markdown("---")

    # --- ฟังก์ชันเสริม LLM (ใช้งานได้เมื่อดึงเนื้อหาจาก URL สำเร็จเท่านั้น) ---
    if article_text:
        
        if has_api_key:
            st.header("✨ ผลการวิเคราะห์ด้วย LLM (ฟังก์ชันเสริม)")
            
            # --- Task 1: ลิสต์คำศัพท์ ---
            st.markdown("### 1. ลิสต์คำศัพท์พร้อมคำแปลและชนิดของคำ")
            
            vocab_system_prompt = (
                "คุณคือผู้เชี่ยวชาญด้านภาษา ทำหน้าที่วิเคราะห์บทความและดึงคำศัพท์สำคัญที่เป็นภาษาอังกฤษ "
                "โดยให้เลือกคำศัพท์ที่น่าสนใจและมีประโยชน์ในการเรียนรู้ภาษาอังกฤษ (ประมาณ 10-15 คำ) "
                "และจัดเรียงตามระดับความยากง่ายของคำ (Easy, Medium, Hard) "
                "พร้อมทั้งระบุชนิดของคำ (Part of Speech) และสร้างประโยคตัวอย่างการใช้คำนั้น "
                "กรุณาตอบกลับในรูปแบบ JSON Array ตาม Schema ที่กำหนด โดยใส่คำแปลและคำอธิบายเป็นภาษาไทย"
            )
            vocab_schema = create_vocab_schema()
            
            vocab_df = get_structured_data_llm(article_text, vocab_system_prompt, vocab_schema, "ลิสต์คำศัพท์")
            
            if vocab_df is not None:
                st.dataframe(vocab_df, use_container_width=True)
                dataframe_to_csv_download_link(vocab_df, filename="vocabulary_list.csv", link_text="⬇️ ดาวน์โหลดลิสต์คำศัพท์ (CSV)")
                
                
            # --- Task 2: โจทย์อ่านจับใจความ (Cloze Test) ---
            st.markdown("### 2. โจทย์อ่านจับใจความ (Cloze Test)")
            
            question_system_prompt = (
                "คุณคือผู้สร้างข้อสอบมืออาชีพ กรุณาสร้างโจทย์ Cloze Test (เติมคำในช่องว่าง) จำนวน 10 ข้อ "
                "จากเนื้อหาบทความที่กำหนดให้ โดยแต่ละข้อให้แทนคำที่หายไปด้วย '____' ในประโยค "
                "จากนั้นให้เขียนเฉลยและคำอธิบายที่ละเอียดว่าทำไมคำตอบนั้นจึงถูกต้อง "
                "คำอธิบายจะต้องเป็นภาษาไทยทั้งหมด และกรุณาตอบกลับในรูปแบบ JSON Array ตาม Schema ที่กำหนด"
            )
            question_schema = create_question_schema()
            
            question_df = get_structured_data_llm(article_text, question_system_prompt, question_schema, "โจทย์ Cloze Test")

            if question_df is not None:
                st.dataframe(question_df, use_container_width=True)
                dataframe_to_csv_download_link(question_df, filename="cloze_test_questions.csv", link_text="⬇️ ดาวน์โหลดโจทย์พร้อมเฉลย (CSV)")
                
                
            # --- Task 3: สรุปบทความ ---
            st.markdown("### 3. สรุปบทความ")
            
            summary_system_prompt = (
                "คุณคือผู้เชี่ยวชาญด้านการศึกษา "
                "กรุณาสรุปบทความที่กำหนดให้เป็นภาษาอังกฤษในความยาวประมาณ 5-7 ประโยค "
                "โดยใช้คำศัพท์และโครงสร้างประโยคที่กระชับและเข้าใจง่าย เหมาะสมสำหรับผู้เรียนระดับมัธยมศึกษาตอนปลาย"
            )
            
            summary_text = get_summary_llm(article_text, summary_system_prompt)
            
            if summary_text:
                st.info(summary_text)
                
            st.markdown("---")
            st.balloons()
            st.success("🎉 การวิเคราะห์บทความทั้งหมดเสร็จสมบูรณ์!")
        else:
            st.warning("⚠️ ไม่พบ Google Gemini API Key. ฟังก์ชัน LLM (ลิสต์คำศัพท์, โจทย์, สรุป) จะไม่ทำงาน. กรุณาใส่ Key ในแถบด้านข้างเพื่อเปิดใช้งานฟังก์ชันเสริม.")


if __name__ == "__main__":
    main()
