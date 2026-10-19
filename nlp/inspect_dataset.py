import pandas as pd

df = pd.read_csv("data/raw/emotion_dataset.csv")

print(df.shape)
print(df.columns.tolist())
print(df.head(10))
print(df["label"].value_counts())