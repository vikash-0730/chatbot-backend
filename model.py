import os
import json
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(BASE_DIR, "data.json")

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# 🔹 Text cleaning function
def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)  # punctuation remove
    return text

# 🔹 Extract texts and labels
texts = [clean_text(d["text"]) for d in data]
labels = [d["intent"] for d in data]

# 🔥 NLP (improved)
vectorizer = TfidfVectorizer(ngram_range=(1,2))
X = vectorizer.fit_transform(texts)

# 🔥 ML Model
model = LogisticRegression(max_iter=200)
model.fit(X, labels)

# 🔹 Prediction function
def predict_intent(user_input):
    user_input = clean_text(user_input)
    X_test = vectorizer.transform([user_input])
    return model.predict(X_test)[0]

# 🔹 Prediction with confidence
def predict_with_confidence(user_input):
    user_input = clean_text(user_input)
    X_test = vectorizer.transform([user_input])

    probs = model.predict_proba(X_test)[0]
    max_prob = max(probs)
    intent = model.classes_[probs.argmax()]

    return intent, float(max_prob)