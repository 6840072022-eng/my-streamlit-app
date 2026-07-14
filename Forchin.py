import streamlit as st
import pandas as pd

hsk5 = pd.read_csv("https://raw.githubusercontent.com/plaktos/hsk_csv/master/hsk5.csv")

hsk6 = pd.read_csv("https://chill-chinese.com/hsk-6-vocabulary-list.csv")

st.write("HSK5 columns:", hsk5.columns.tolist())

st.write("HSK6 columns:", hsk6.columns.tolist())
# -----------------------------
# URL ของแต่ละระดับ
# -----------------------------
LEVEL_URLS = {
    "HSK5": "https://raw.githubusercontent.com/plaktos/hsk_csv/master/hsk5.csv",
    "HSK6": "https://chill-chinese.com/hsk-6-vocabulary-list.csv"
}

# -----------------------------
# โหลดข้อมูล (Cache)
# -----------------------------
@st.cache_data
def load_hsk(level):
    url = LEVEL_URLS[level]
    return pd.read_csv(url)

# -----------------------------
# เลือกระดับ
# -----------------------------
level = st.sidebar.selectbox(
    "เลือกระดับ HSK",
    list(LEVEL_URLS.keys())
)

# โหลดข้อมูลอัตโนมัติ
df = load_hsk(level)

st.success(f"โหลด {level} สำเร็จ!")

# ดูข้อมูลตัวอย่าง
st.dataframe(df.head())
