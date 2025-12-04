import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
# Import Google GenAI (ต้องติดตั้ง: pip install google-generativeai)
try:
    from google import genai
    from google.genai.errors import APIError
except ImportError:
    genai = None
    APIError = None

st.set_page_config(page_title="Smart Article Analyzer", layout="wide")

st.title("📝 Smart Article Analyzer & Q&A Generator (Powered by Gemini)")

# Sidebar
st.sidebar.header("Settings")
# เปลี่ยนชื่อ input ให้ชัดเจนขึ้นสำหรับ Gemini API Key
api_key = st.sidebar.text_input("Gemini API Key", type="password")
num_questions = st.sidebar.number_input("Number of Cloze/Q&A", min_value=1, max_value=20, value=10)
output_language = st.sidebar.selectbox("Output Language", ["English", "French", "Thai"])
vocab_level = st.sidebar.selectbox("Vocabulary Level", ["Easy", "Medium", "Hard"])

# Main input
st.header("Input Article URL")
url = st.text_input("Enter article URL:")

# ----------------- JSON Schema Definition -----------------
# กำหนดโครงสร้าง JSON ที่ต้องการจาก LLM เพื่อให้แน่ใจว่าได้ข้อมูลครบถ้วน
def create_json_schema(num_q, lang, level):
    return {
        "type": "OBJECT",
        "properties": {
            "summary": {
                "type": "STRING", 
                "description": f"A concise summary of the article in {lang}. Must be comprehensive, not just the first few sentences."
            },
            "qna": {
                "type": "ARRAY",
                "description": f"A list of exactly {num_q} cloze test or Q&A questions, including answers and explanations.",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "question": {"type": "STRING", "description": "The cloze test or question text."},
                        "answer": {"type": "STRING", "description": "The correct answer or missing word."},
                        "explanation": {"type": "STRING", "description": "A brief explanation for the answer."}
                    },
                    "required": ["question", "answer", "explanation"]
                }
            },
            "vocabulary": {
                "type": "ARRAY",
                "description": f"A list of important vocabulary from the article suitable for {level} learners.",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "word": {"type": "STRING", "description": "The vocabulary word."},
                        "translation": {"type": "STRING", "description": f"Translation/Definition in {lang}."},
                        "part_of_speech": {"type": "STRING", "description": "Part of speech (e.g., Noun, Verb)."},
                        "difficulty": {"type": "STRING", "description": f"Difficulty level based on the article's context, choose from {level}."}
                    },
                    "required": ["word", "translation", "part_of_speech", "difficulty"]
                }
            }
        },
        "required": ["summary", "qna", "vocabulary"]
    }


if st.button("Analyze Article") and url:
    if not api_key:
        st.error("⚠️ กรุณากรอก Gemini API Key ในแถบด้านข้าง (Settings) ก่อนเริ่มการวิเคราะห์")
        st.stop()
    
    if not genai:
        # แก้ไขข้อความแจ้งเตือนการติดตั้ง
        st.error("⚠️ ไม่พบไลบรารี Google GenAI โปรดติดตั้งด้วยคำสั่ง: pip install google-generativeai")
        st.stop()

    # 1️⃣ Fetch article content
    with st.spinner("1/2: กำลังดึงเนื้อหาบทความ..."):
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(res.text, "html.parser")
            paragraphs = soup.find_all("p")
            article_text = "\n".join([p.get_text() for p in paragraphs])
            
            if not article_text or len(article_text) < 100:
                 # ลองหา content อื่นๆ ในกรณีที่ไม่มี <p> tag
                article_text = soup.get_text()[:3000] # จำกัดขนาดเพื่อป้องกันโอเวอร์โหลด
                if len(article_text) < 100:
                    st.error("Failed to extract meaningful article text.")
                    st.stop()
            
            st.subheader("Article Preview")
            st.write(article_text[:500] + "...")
            
        except Exception as e:
            st.error(f"Failed to fetch or parse article URL: {e}")
            st.stop()
    
    # 2️⃣ Prepare LLM call
    client = genai.Client(api_key=api_key)
    
    system_instruction = f"""
    You are an advanced language analyzer assistant. Your task is to analyze the provided article text and generate a structured JSON output according to the user's detailed requirements and the strict JSON schema provided.
    - Summary must be complete and concise.
    - Q&A must be exactly {num_questions} items.
    - All output strings must be properly escaped for JSON.
    """

    user_prompt = f"""
    Analyze the following article and generate all required outputs.

    Article Text:
    ---
    {article_text}
    ---
    
    Specific Requirements:
    1. Summarize the article completely in {output_language}.
    2. Generate exactly {num_questions} items for the Q&A/Cloze Test.
    3. Extract vocabulary suitable for a {vocab_level} level, and provide the translation in {output_language}.
    """
    
    # 3️⃣ Call Gemini with Structured Output
    with st.spinner("2/2: กำลังวิเคราะห์บทความด้วย Gemini API..."):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[user_prompt],
                system_instruction=system_instruction,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": create_json_schema(num_questions, output_language, vocab_level),
                }
            )
            
            # The JSON output is in response.text
            llm_response_text = response.text
            
        except APIError as e:
            st.error(f"Gemini API Error: {e.status_code}. Please check your API Key and quotas.")
            st.stop()
        except Exception as e:
            st.error(f"An unexpected error occurred during API call: {e}")
            st.stop()
    
    # 4️⃣ Process and Display results
    try:
        data = json.loads(llm_response_text)
        
        # A. Display Summary (Addressing the user's concern about truncation)
        summary = data.get("summary", "Summary not found in LLM output.")
        st.subheader(f"✅ Summary ({output_language})")
        st.success(summary)
        
        # B. Prepare DataFrames
        qna_df = pd.DataFrame(data.get("qna", []))
        vocab_df = pd.DataFrame(data.get("vocabulary", []))
        
    except Exception as e:
        st.error(f"⚠️ Failed to parse LLM output JSON: {e}")
        st.write("Raw LLM Response (for debugging):")
        st.code(llm_response_text, language="json")
        qna_df = pd.DataFrame()
        vocab_df = pd.DataFrame()
        
    # C. Display Q&A/Cloze Test
    if not qna_df.empty:
        st.subheader(f"❓ Cloze Test / Q&A ({len(qna_df)} items)")
        # Rename columns for better readability in Thai context
        qna_df.columns = ["คำถาม / Cloze", "คำตอบ", "คำอธิบาย"]
        st.dataframe(qna_df, use_container_width=True)
        st.download_button(
            "⬇️ Download Q&A CSV", 
            qna_df.to_csv(index=False).encode('utf-8'), 
            "qna.csv",
            mime="text/csv"
        )
    
    # D. Display Vocabulary
    if not vocab_df.empty:
        st.subheader(f"📚 Vocabulary Table (Level: {vocab_level})")
        # Rename columns for better readability
        vocab_df.columns = ["คำศัพท์", f"คำแปล ({output_language})", "ชนิดของคำ", "ระดับความยาก"]
        st.dataframe(vocab_df, use_container_width=True)
        st.download_button(
            "⬇️ Download Vocabulary CSV", 
            vocab_df.to_csv(index=False).encode('utf-8'), 
            "vocabulary.csv",
            mime="text/csv"
        )