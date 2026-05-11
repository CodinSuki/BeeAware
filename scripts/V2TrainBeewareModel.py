import pandas as pd
import pickle
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / 'data' / 'processed' / 'V2beeware_master_training.csv'
MODEL_DIR = BASE_DIR / 'models'
MODEL_DIR.mkdir(parents=True, exist_ok=True)

ROW_CAP = 3000


print("Loading master dataset...")
df = pd.read_csv(DATA_PATH).dropna()
df['quadrant'] = df['quadrant'].astype(int)

print("\n--- Raw Quadrant Counts ---")
print(df['quadrant'].value_counts().sort_index())


print("\nBalancing quadrants...")
balanced_parts = []
for q in sorted(df['quadrant'].unique()):
    subset = df[df['quadrant'] == q]
    n = min(ROW_CAP, len(subset))
    balanced_parts.append(subset.sample(n=n, random_state=42))
    print(f"  Q{q}: {len(subset)} -> {n} rows")

df_balanced = pd.concat(balanced_parts, ignore_index=True)

print("\n--- Balanced Quadrant Counts ---")
print(df_balanced['quadrant'].value_counts().sort_index())


X = df_balanced['window_title']
y = df_balanced['quadrant']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)


print("\nVectorizing with bigrams...")
vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    max_features=10000,
    stop_words=None,
    lowercase=True,
    token_pattern=r'(?u)\b[A-Za-z0-9]+\b'
)

X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf = vectorizer.transform(X_test)


print("Training SVM...")
model = LinearSVC(
    random_state=42,
    dual=False,
    max_iter=5000
)

model.fit(X_train_tfidf, y_train)


print("\n--- Model Performance Report ---")
y_pred = model.predict(X_test_tfidf)
print(classification_report(y_test, y_pred, target_names=['Q0 Urgent', 'Q1 Deep Work', 'Q2 Reactive', 'Q3 Distraction']))


print(f"\nSaving model to {MODEL_DIR}...")
with open(MODEL_DIR / 'V2eisenhower_model.pkl', 'wb') as f:
    pickle.dump(model, f)
with open(MODEL_DIR / 'V2tfidf_vectorizer.pkl', 'wb') as f:
    pickle.dump(vectorizer, f)

print("Done.")