import pandas as pd
import streamlit as st

st.title("UrbanPulse Dashboard")

df = pd.read_csv("data/raw/complaints.csv", dtype={"id": str})

st.subheader("All complaints")
st.dataframe(df)

st.subheader("Complaints by emotion")
st.bar_chart(df["emotion"].value_counts())

st.subheader("Complaints by area")
st.bar_chart(df["area"].value_counts())