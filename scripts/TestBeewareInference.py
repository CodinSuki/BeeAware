import pickle
import pandas as pd
from pathlib import Path

# Load the Brain
MODEL_PATH = Path('models/eisenhower_model.pkl')
VECTOR_PATH = Path('models/tfidf_vectorizer.pkl')

with open(MODEL_PATH, 'rb') as f:
    model = pickle.load(f)
with open(VECTOR_PATH, 'rb') as f:
    vectorizer = pickle.load(f)

# Mapping for humans
quadrants = {0: "Q1: URGENT", 1: "Q2: GROWTH", 2: "Q3: NOISE", 3: "Q4: PLAY"}

def predict_window(title):
    # 1. Convert text to math
    tfidf_title = vectorizer.transform([title])
    # 2. Predict
    prediction = model.predict(tfidf_title)[0]
    # 3. Get Confidence (Probability)
    probs = model.predict_proba(tfidf_title)[0]
    confidence = max(probs)
    
    print(f"Title: {title}")
    print(f"AI Guess: {quadrants[prediction]} ({confidence:.2%} confidence)\n")

# --- TEST CASES ---
test_titles = [
    "emu8086 - [My_First_Program.asm]",    # Should be Q2
    "Blackboard Learn - Final Quiz",       # Should be Q1
    "Discord - New Message from Sky",      # Should be Q3
    "Wuthering Waves - Version 1.1",       # Should be Q4
    "PostgreSQL - Query Tool"               # Should be Q2
]

for t in test_titles:
    predict_window(t)