
from pathlib import Path

import pandas as pd
import streamlit as st

# Project directory
BASE_DIR = Path(__file__).resolve().parents[1]

COMPLAINTS_FILE = BASE_DIR / "data" / "raw" / "complaints.csv"
LABELED_FILE = BASE_DIR / "data" / "labeled_civic.csv"

st.set_page_config(
    page_title="UrbanPulse",
    page_icon="🏙️",
    layout="wide"
)

st.title("UrbanPulse Dashboard")
st.caption("AI-Based Civic Feedback and Infrastructure Monitoring")

# Prefer submitted complaints; otherwise show the existing dataset
if COMPLAINTS_FILE.exists() and COMPLAINTS_FILE.stat().st_size > 0:
    df = pd.read_csv(COMPLAINTS_FILE)
    data_source = "Submitted civic complaints"
elif LABELED_FILE.exists():
    df = pd.read_csv(LABELED_FILE)
    data_source = "Existing labeled civic dataset"
else:
    st.error("No civic feedback dataset was found.")
    st.stop()

if df.empty:
    st.warning("The dataset is currently empty.")
    st.stop()

if "emotion" not in df.columns or "text" not in df.columns:
    st.error("Dataset must contain 'text' and 'emotion' columns.")
    st.stop()

st.info(f"Data source: {data_source}")

# Summary metrics
col1, col2, col3 = st.columns(3)

col1.metric("Total Feedback", len(df))
col2.metric("Emotion Categories", df["emotion"].nunique())
col3.metric(
    "Areas Reported",
    df["area"].nunique() if "area" in df.columns else "Not available"
)

st.divider()

# Emotion distribution
st.subheader("Emotion Distribution")
st.bar_chart(df["emotion"].value_counts())

# Area distribution, only when location data exists
if "area" in df.columns:
    st.subheader("Complaints by Area")
    st.bar_chart(df["area"].value_counts())
else:
    st.warning(
        "Area information is not available in this dataset. "
        "Area-wise visualizations will appear when complaints "
        "are submitted through the reporting form."
    )

st.subheader("Civic Feedback Records")
st.dataframe(df, use_container_width=True)
