
# Streamlit Exam Prep App (Part 1)

import streamlit as st
import pandas as pd
import random
import io

st.set_page_config(page_title="Vocab Master — Exam Prep", layout="wide")

# ----------------------------- Mock LLM -----------------------------
def call_llm_mock(prompt: str) -> str:
    prompt_lower = prompt.lower()

    if "generate vocab" in prompt_lower:
        n = 10
        import re
        m = re.search(r"(\d{1,3}) words", prompt_lower)
        if m:
            n = int(m.group(1))

        topic = "general"
        m = re.search(r"topic:\s*(\w+)", prompt_lower)
        if m:
            topic = m.group(1)

        rows = []
        for i in range(n):
            word = f"{topic}_word{i+1}"
            rows.append(
                f"{word} | noun | meaning of {word} | Example sentence using {word}."
            )
        return "\n".join(rows)

    if "make a passage" in prompt_lower:
        topic = "the topic"
        import re
        m = re.search(r"topic:\s*([\w ]+)", prompt_lower)
        if m:
            topic = m.group(1)

        passage = (
            f"This short passage discusses {topic}. It explains key ideas in simple language."
        )
        questions = (
            "Q1: What is the main idea?\n"
            "Q2: Mention one detail.\n"
            "Q3: What does 'key ideas' mean in context?"
        )
        return passage + "\n\n" + questions

    return "(mock) " + prompt[:100]

def parse_vocab_from_llm(text: str) -> pd.DataFrame:
    rows = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue

        rows.append({
            "Word": parts[0],
            "Part of Speech": parts[1],
            "Meaning": parts[2],
            "Example": parts[3] if len(parts) > 3 else "",
            "Synonyms": "",
            "Difficulty": random.choice(["Easy", "Medium", "Hard"]),
        })
    return pd.DataFrame(rows)

def generate_mcq_from_vocab(df: pd.DataFrame, n_questions: int = 10) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    pool = df.to_dict(orient="records")
    questions = []

    for i in range(min(n_questions, len(pool))):
        correct = pool[i]
        others = [p for p in pool if p["Word"] != correct["Word"]]
        distractors = random.sample(others, k=min(3, len(others)))

        options = [d["Word"] for d in distractors] + [correct["Word"]]
        random.shuffle(options)

        questions.append({
            "No": i+1,
            "Question": f"Which word matches this meaning: {correct['Meaning']}",
            "A": options[0] if len(options) > 0 else "",
            "B": options[1] if len(options) > 1 else "",
            "C": options[2] if len(options) > 2 else "",
            "D": options[3] if len(options) > 3 else "",
            "Answer": correct["Word"]
        })
    return pd.DataFrame(questions)
def generate_passage_and_questions(topic: str):
    prompt = f"Make a passage and questions. Topic: {topic}"
    text = call_llm_mock(prompt)
    parts = text.split("\n\n")

    return {
        "passage": parts[0] if len(parts) > 0 else "",
        "questions": parts[1] if len(parts) > 1 else "",
    }

st.title("Vocab Master — English Exam Prep")

if "vocab_df" not in st.session_state:
    st.session_state.vocab_df = pd.DataFrame()

with st.sidebar:
    st.header("Settings")
    topic = st.text_input("Topic", "travel")
    num_words = st.slider("Number of words", 5, 50, 15)
    n_quiz = st.slider("Number of quiz questions", 5, 30, 10)

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Generate Vocab", "Quiz", "Passage", "Flashcards", "Export"]
)

# -------- Tab 1 --------
with tab1:
    if st.button("Generate Vocabulary"):
        raw = call_llm_mock(f"Generate {num_words} words for topic: {topic}")
        df = parse_vocab_from_llm(raw)
        st.session_state.vocab_df = df
        st.success("Vocabulary generated!")

    if not st.session_state.vocab_df.empty:
        st.dataframe(st.session_state.vocab_df)
        st.download_button(
            "Download CSV",
            st.session_state.vocab_df.to_csv(index=False),
            file_name=f"vocab_{topic}.csv"
        )

with tab2:
    if st.button("Generate Quiz"):
        st.session_state.quiz_df = generate_mcq_from_vocab(
            st.session_state.vocab_df,
            n_questions=n_quiz
        )
    if "quiz_df" in st.session_state:
        st.dataframe(st.session_state.quiz_df)

# -------- Tab 3 --------
with tab3:
    pass_topic = st.text_input("Passage Topic", topic)
    if st.button("Generate Passage"):
        st.session_state.passage = generate_passage_and_questions(pass_topic)
    if "passage" in st.session_state:
        st.subheader("Passage")
        st.write(st.session_state.passage["passage"])
        st.subheader("Questions")
        st.text(st.session_state.passage["questions"])

# -------- Tab 4 --------
with tab4:
    df = st.session_state.vocab_df
    if df.empty:
        st.info("Generate vocab first.")
    else:
        idx = st.number_input("Word index", 1, len(df), 1)
        row = df.iloc[idx - 1]
        st.write(f"### {row['Word']} ({row['Part of Speech']})")
        if st.button("Reveal Meaning"):
            st.write(row["Meaning"])
            st.write(row["Example"]) 

with tab5:
    if not st.session_state.vocab_df.empty:
        buf = io.StringIO()
        buf.write("Vocabulary:\n")
        buf.write(st.session_state.vocab_df.to_csv(index=False))
        buf.write("\n\nQuiz:\n")
        if "quiz_df" in st.session_state:
            buf.write(st.session_state.quiz_df.to_csv(index=False))
        buf.write("\n\nPassage:\n")
        if "passage" in st.session_state:
            buf.write(st.session_state.passage["passage"])
            buf.write("\n\n" + st.session_state.passage["questions"])

        st.download_button(
            "Download Study Package",
            buf.getvalue(),
            file_name="study_package.txt"
        )
    else:
        st.info("Generate vocabulary first.")


