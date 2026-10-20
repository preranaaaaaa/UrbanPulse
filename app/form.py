import os
from datetime import datetime

import joblib
import pandas as pd
import streamlit as st
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

AREAS = ["Hampankatta", "Kankanady", "Surathkal", "Lalbagh",
         "Bejai", "Kadri", "Pumpwell", "Jyothi"]
CATEGORIES = ["Road", "Drainage", "Water", "Garbage", "Transport", "Other"]
CSV_PATH = "data/raw/complaints.csv"


@st.cache_resource
def load_tools():
    vectorizer, model = joblib.load("models/baseline.joblib")
    return vectorizer, model, SentimentIntensityAnalyzer()


vectorizer, model, vader = load_tools()

st.title("UrbanPulse: Report a Civic Issue")

area = st.selectbox("Area", AREAS)
category = st.selectbox("Category", CATEGORIES)
text = st.text_area("Describe the problem")

if st.button("Submit"):
    if text.strip() == "":
        st.warning("Please describe the problem first.")
    else:
        emotion = model.predict(vectorizer.transform([text]))[0]
        compound = vader.polarity_scores(text)["compound"]
        intensity = round(1 + 4 * abs(compound))

        row = {
            "id": datetime.now().strftime("%Y%m%d-%H%M%S-%f"),
            "text": text.strip(),
            "area": area,
            "category": category,
            "source": "form",
            "timestamp": datetime.now().isoformat(),
            "intensity": intensity,
            "emotion": emotion,
        }
        df = pd.DataFrame([row])
        df.to_csv(CSV_PATH, mode="a", header=not os.path.exists(CSV_PATH), index=False)
        st.success(f"Recorded! Detected emotion: {emotion} (intensity {intensity}/5)")