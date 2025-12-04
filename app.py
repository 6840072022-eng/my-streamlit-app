import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json

# Optional: ถ้าอยากใช้ LLM จริง ๆ
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

st.set_page_config(page_title="Smart Article Analyzer", layout="wide")

st.title("📝 Smart Article Analyzer & Q&A Generator")

# Sidebar
st.sidebar.header("Settings")
api_key = st.sidebar.text_input("Optional OpenAI / Gemini API Key", type="password")
num_questions = st.sidebar.number_input("Number of Cloze/Q&A", min_value=1, max_value=20, value=10)
output_language = st.sidebar.selectbox("Output Language", ["English", "French", "Thai"])
vocab_level = st.sidebar.selectbox("Vocabulary Level", ["Easy", "Medium", "Hard"])

# Main input
st.header("Input Article URL")
url = st.text_input("Enter article URL:")

if st.button("Analyze Article") and url:
    # 1️⃣ Fetch article content
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        paragraphs = soup.find_all("p")
        article_text = "\n".join([p.get_text() for p in paragraphs])
        st.subheader("Article Preview")
        st.write(article_text[:1000] + "...")
    except Exception as e:
        st.error(f"Failed to fetch article: {e}")
        st.stop()
    
    # 2️⃣ Prepare LLM prompt
    prompt = f"""
Analyze the following article:
{article_text}

Tasks:
1. Summarize the article in a concise way ({output_language}).
2. Generate {num_questions} cloze test / Q&A questions with answers and explanations.
3. Extract important vocabulary with columns: word, translation, part_of_speech, difficulty ({vocab_level}).
Format the output as JSON with two keys: 'qna' and 'vocabulary'.
"""
    llm_response = None
    
    # 3️⃣ Optional LLM analysis
    if api_key and OpenAI:
        client = OpenAI(api_key=api_key)
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            llm_response = response.choices[0].message.content
        except Exception as e:
            st.warning(f"LLM request failed: {e}")
            llm_response = None
    
    if llm_response:
        try:
            data = json.loads(llm_response)
            qna_df = pd.DataFrame(data.get("qna", []))
            vocab_df = pd.DataFrame(data.get("vocabulary", []))
        except Exception as e:
            st.warning(f"Failed to parse LLM output: {e}")
            qna_df = pd.DataFrame()
            vocab_df = pd.DataFrame()
    else:
        # Fallback if no API key or LLM fails: simple summary and empty tables
        summary = article_text[:500] + "..." if len(article_text) > 500 else article_text
        st.subheader("Summary")
        st.write(summary)
        qna_df = pd.DataFrame(columns=["Question", "Answer", "Explanation"])
        vocab_df = pd.DataFrame(columns=["Word", "Translation", "Part_of_Speech", "Difficulty"])
    
    # 4️⃣ Display results
    if not qna_df.empty:
        st.subheader("Cloze / Q&A")
        st.dataframe(qna_df)
        st.download_button("Download Q&A CSV", qna_df.to_csv(index=False), "qna.csv")
    
    if not vocab_df.empty:
        st.subheader("Vocabulary Table")
        st.dataframe(vocab_df)
        st.download_button("Download Vocabulary CSV", vocab_df.to_csv(index=False), "vocabulary.csv")

