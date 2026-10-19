import os
from datetime import datetime

import pandas as pd
import streamlit as st

AREAS = ["Hampankatta", "Kankanady", "Surathkal", "Lalbagh",
         "Bejai", "Kadri", "Pumpwell", "Jyothi"]
CATEGORIES = ["Road", "Drainage", "Water", "Garbage", "Transport", "Other"]
CSV_PATH = "data/raw/complaints.csv"

st.title("UrbanPulse: Report a Civic Issue")

area = st.selectbox("Area", AREAS)
category = st.selectbox("Category", CATEGORIES)
text = st.text_area("Describe the problem")
user_rating = st.slider("How serious is it? (1 = minor, 5 = severe)", 1, 5, 3)

if st.button("Submit"):
    if text.strip() == "":
        st.warning("Please describe the problem first.")
    else:
        row = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
            "text": text.strip(),
            "area": area,
            "category": category,
            "source": "form",
            "timestamp": datetime.now().isoformat(),
            "user_rating": user_rating,
        }
        df = pd.DataFrame([row])
        df.to_csv(CSV_PATH, mode="a", header=not os.path.exists(CSV_PATH), index=False)
        st.success("Thank you! Your complaint has been recorded.")