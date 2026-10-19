import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report

df = pd.read_csv("data/raw/emotion_mapped.csv")

X_train, X_test, y_train, y_test = train_test_split(
    df["text"], df["emotion"],
    test_size=0.2, random_state=42, stratify=df["emotion"]
)

vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2)
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

model = LogisticRegression(max_iter=1000, class_weight="balanced")
model.fit(X_train_vec, y_train)

print(classification_report(y_test, model.predict(X_test_vec)))
tests = [
    "Pothole near the bus stand has damaged my bike again, fed up!",
    "Garbage not collected for a week, terrible smell",
    "The new bus shelter is clean and very useful, thank you",
    "The drain has been blocked for 3 weeks",
    "Street lights were fixed quickly, good work",
]
print()
for t, p in zip(tests, model.predict(vectorizer.transform(tests))):
    print(p, "<-", t)
civic = pd.read_csv("data/labeled_civic.csv")
civic["predicted"] = model.predict(vectorizer.transform(civic["text"]))

print()
print("Accuracy on civic sentences:", (civic["predicted"] == civic["emotion"]).mean())
print(civic[civic["predicted"] != civic["emotion"]][["text", "emotion", "predicted"]])