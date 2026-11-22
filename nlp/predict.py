import joblib
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

try:
    _vectorizer, _model = joblib.load("models/baseline.joblib")
except Exception:
    _vectorizer, _model = None, None

_vader = SentimentIntensityAnalyzer()


def analyze_text(text):
    """Return (emotion, intensity) for a civic complaint text."""
    if _model is not None and _vectorizer is not None:
        emotion = _model.predict(_vectorizer.transform([text]))[0]
    else:
        # Fallback when model file is missing
        compound = _vader.polarity_scores(text)["compound"]
        if compound <= -0.5:
            emotion = "Angry"
        elif compound <= -0.05:
            emotion = "Frustrated"
        elif compound >= 0.5:
            emotion = "Happy"
        elif compound >= 0.05:
            emotion = "Satisfied"
        else:
            emotion = "Neutral"

    compound = _vader.polarity_scores(text)["compound"]
    if compound <= -0.05 and emotion in ("Happy", "Satisfied"):
        emotion = "Angry" if compound <= -0.5 else "Frustrated"

    base = {"Angry": 4, "Frustrated": 3, "Neutral": 1, "Satisfied": 1, "Happy": 1}.get(emotion, 1)
    intensity = min(5, base + round(abs(compound)))
    return emotion, intensity
