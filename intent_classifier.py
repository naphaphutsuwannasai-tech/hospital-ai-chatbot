import pickle
import re

model = pickle.load(open("intent_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

def normalize_text(text):
    text = text.lower()
    text = re.sub(r"[^\w\sก-๙]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def detect_intent(text: str) -> str:
    text = normalize_text(text)
    X = vectorizer.transform([text])
    probs = model.predict_proba(X)[0]
    max_prob = max(probs)

    if max_prob < 0.60:
        return "unknown"

    return model.classes_[probs.argmax()]
