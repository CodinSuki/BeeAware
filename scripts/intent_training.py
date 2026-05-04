import pandas as pd
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, classification_report

os.makedirs('models', exist_ok=True)

df = pd.read_csv('data/processed/youtube_training_data.csv')


def map_label(category):
    cat_str = str(category).lower()
    if 'educational' in cat_str or 'study' in cat_str:
        return 1
    return 0

df['is_study'] = df['content_type'].apply(map_label)

X = df['title']
y = df['is_study']

vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
X_vectorized = vectorizer.fit_transform(X.astype(str))

X_train, X_test, y_train, y_test = train_test_split(X_vectorized, y, test_size=0.2, random_state=42)

clf = MultinomialNB()
clf.fit(X_train, y_train)

y_pred = clf.predict(X_test)

print("--- YOUTUBE INTENT BRAIN (V2) ---")
print(f"Accuracy: {accuracy_score(y_test, y_pred):.2%}")
print("\nDetailed Report:")

print(classification_report(y_test, y_pred, target_names=['Distraction (0)', 'Study (1)']))

with open('models/youtube_intent_model.pkl', 'wb') as f:
    pickle.dump(clf, f)
with open('models/youtube_vectorizer.pkl', 'wb') as f:
    pickle.dump(vectorizer, f)