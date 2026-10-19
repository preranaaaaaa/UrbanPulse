from datasets import load_dataset

ds = load_dataset("dair-ai/emotion", split="train")
df = ds.to_pandas()
df.to_csv("data/raw/emotion_dataset.csv", index=False)
print(df.shape)
print(df.head())