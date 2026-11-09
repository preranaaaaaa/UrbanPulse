import joblib
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_vectorizer, _model = joblib.load("models/baseline.joblib")
_vader = SentimentIntensityAnalyzer()


def analyze_text(text):
    emotion = _model.predict(_vectorizer.transform([text]))[0]
    compound = _vader.polarity_scores(text)["compound"]
    if compound <= -0.05 and emotion in ("Happy", "Satisfied"):
        emotion = "Angry" if compound <= -0.5 else "Frustrated"
    base = {"Angry": 4, "Frustrated": 3, "Neutral": 1, "Satisfied": 1, "Happy": 1}[emotion]
    return emotion, min(5, base + round(abs(compound)))
