
import streamlit as st
import pandas as pd
from openai import OpenAI

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="English Helper App", layout="wide")

st.title("📘 English Learning Assistant (TOEIC / IELTS / Eng I & II)")

# Sidebar for API key
st.sidebar.header("🔑 API Settings")
api_key = st.sidebar.text_input("Enter your OpenAI API key:", type="password")

task = st.sidebar.selectbox(
    "Select Task",
    [
        "Summarize Text",
        "Extract Vocabulary",
        "Generate Exam Questions",
    ]
)

# -----------------------------
# LLM Helper
# -----------------------------
def run_llm(prompt, api_key, google_api_key):
    # ถ้ามี OpenAI key → ใช้ OpenAI
    if api_key and len(api_key) > 5:
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=prompt
            )
            return response.output_text
        except Exception as e:
            st.error("❌ OpenAI Error – switching to Gemini automatically")
            st.write(e)
            # ถ้า error → ใช้ Gemini ต่อ
    
    # ถ้าไม่มี OpenAI key หรือ error → ใช้ Gemini
    genai.configure(api_key=google_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    gemini_response = model.generate_content(prompt)
    return gemini_response.text



# -----------------------------
# Download Helper
# -----------------------------
def download_dataframe(df, filename="output.csv"):
    return df.to_csv(index=False).encode("utf-8")


# -----------------------------
# Main UI
# -----------------------------
st.subheader("📝 Input Your Text or Upload File")

user_text = st.text_area("Enter your text here:", height=180)

uploaded_file = st.file_uploader(
    "Or upload CSV / Excel file",
    type=["csv", "xlsx"]
)

df_input = None

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df_input = pd.read_csv(uploaded_file)
    else:
        df_input = pd.read_excel(uploaded_file)

    st.write("📄 **Uploaded Data**")
    st.dataframe(df_input)


# -----------------------------
# Process Button
# -----------------------------
if st.button("Run"):
    
    if not api_key:
        st.error("❌ Please enter your API key in the sidebar.")
        st.stop()

    # Case 1 — Text input
    if user_text.strip() != "":
        final_input = user_text

    # Case 2 — File upload
    elif df_input is not None:
        # Convert entire dataframe into text
        final_input = df_input.to_string()

    else:
        st.warning("⚠ Please enter text or upload a file.")
        st.stop()

    # Build prompt
    if task == "Summarize Text":
        prompt = f"Summarize this text for a TOEIC/IELTS learner:\n{final_input}"

    elif task == "Extract Vocabulary":
        prompt = (
            "Extract difficult vocabulary from the following text. "
            "Return results in a table with columns: word, part_of_speech, meaning, example_sentence.\n"
            f"Text:\n{final_input}"
        )

    elif task == "Generate Exam Questions":
        prompt = (
            "Create 10 TOEIC/IELTS-style questions based on the following text. "
            "Return a table with columns: question, choice_A, choice_B, choice_C, choice_D, answer.\n"
            f"Text:\n{final_input}"
        )

    # Run LLM
    with st.spinner("Generating results..."):
        llm_output = run_llm(prompt, api_key)

    st.subheader("📘 Output")
    st.write(llm_output)

    # Try converting to dataframe
    try:
        df = pd.read_csv(pd.compat.StringIO(llm_output))
        st.dataframe(df)

        st.download_button(
            "⬇ Download as CSV",
            data=download_dataframe(df),
            file_name="result.csv",
            mime="text/csv",
        )
    except:
        st.info("ℹ The result is text (not a table), shown above.")


# -----------------------------
# Footer
# -----------------------------
st.markdown("---")
st.caption("For learners preparing for TOEIC / IELTS / Eng I & II. Built with Streamlit + OpenAI.")

