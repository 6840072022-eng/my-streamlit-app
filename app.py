"""


import streamlit as st
import pandas as pd
import random
import io
from typing import List, Dict, Any


st.set_page_config(page_title="Vocab Master — Exam Prep", layout="wide")


# ----------------------------- Helper LLM functions -----------------------------


def call_llm_mock(prompt: str) -> str:
"""A simple deterministic mock 'LLM' used so the app works without external APIs.
Replace this function with a real API call to Google Gemini or OpenAI.
"""
# Very small mock: return canned responses based on prompt keywords.
prompt_lower = prompt.lower()
if "generate vocab" in prompt_lower:
# extract requested number
n = 10
try:
import re
m = re.search(r"(\d{1,3}) words", prompt_lower)
if m:
n = int(m.group(1))
except Exception:
n = 10
topic = "general"
m = re.search(r"topic:\s*(\w+)", prompt_lower)
if m:
topic = m.group(1)
words = [f"{topic}_word{i+1}" for i in range(n)]
rows = []
for w in words:
rows.append(f"{w} | noun | meaning of {w} | Example sentence using {w} in context.")
return "\n".join(rows)


if "make a passage" in prompt_lower:
topic = "the topic"
try:
import re
m = re.search(r"topic:\s*([\w ]+)", prompt_lower)
if m:
topic = m.group(1)
except Exception:
topic = "the topic"
passage = (
f"This short passage discusses {topic}. It includes key terms and presents a short idea that can be used for comprehension question. "
"Students should read carefully and answer questions based on details, inference, and vocabulary-in-context."
)
st.caption("This app is a prototype. Replace the mock LLM function with a real API call to Google Gemini or OpenAI for production use.")

