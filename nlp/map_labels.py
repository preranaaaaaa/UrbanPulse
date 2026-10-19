import pandas as pd

df = pd.read_csv("data/raw/emotion_dataset.csv")

label_map = {
    0: "Frustrated",   # sadness
    1: "Happy",        # joy
    2: "Satisfied",    # love
    3: "Angry",        # anger
    4: "Frustrated",   # fear
}

df["emotion"] = df["label"].map(label_map)
df = df.dropna(subset=["emotion"])      # drops label 5 (surprise)

df[["text", "emotion"]].to_csv("data/raw/emotion_mapped.csv", index=False)
print(df["emotion"].value_counts())