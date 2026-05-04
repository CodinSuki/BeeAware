import pandas as pd
import pickle
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report

# 1. SETUP PATHS
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / 'data' / 'processed' / 'beeware_master_training.csv'
MODEL_DIR = BASE_DIR / 'models'
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# 2. LOAD & UNDERSAMPLE DATA
print("Loading master dataset...")
df = pd.read_csv(DATA_PATH).dropna()

df_q0 = df[df['quadrant'] == 0.0]
df_q1 = df[df['quadrant'] == 1.0]
df_q2 = df[df['quadrant'] == 2.0]
df_q3 = df[df['quadrant'] == 3.0]

# Keep the undersampling to ensure a clean, fast training environment
n_samples = min(3000, len(df_q3))
df_q3_downsampled = df_q3.sample(n=n_samples, random_state=42)

df_balanced = pd.concat([df_q0, df_q1, df_q2, df_q3_downsampled])

X = df_balanced['window_title']
y = df_balanced['quadrant']

# 3. SPLIT DATA
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. FEATURE EXTRACTION
# 4. FEATURE EXTRACTION
print("Vectorizing with Bigrams (Universal Patterns)...")
vectorizer = TfidfVectorizer(
    ngram_range=(1, 2), 
    max_features=10000, 
    stop_words=None, 
    lowercase=True,
    # THE FIX: This Regex tells the AI to only read letters (A-Z, a-z) and completely ignore numbers
    token_pattern=r'(?u)\b[A-Za-z]+\b' 
)
X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf = vectorizer.transform(X_test)

# 5. THE SVM UPGRADE
print("Training the Universal SVM Brain...")
model = LinearSVC(
    random_state=42, 
    dual=True,          # Keep this for speed
    max_iter=5000       # Keep this for safety
    # Removed class_weight because the dataset is already balanced physically
)
model.fit(X_train_tfidf, y_train)

# 6. EVALUATION
print("\n--- GENERAL MODEL PERFORMANCE REPORT ---")
y_pred = model.predict(X_test_tfidf)
print(classification_report(y_test, y_pred))

# 7. SAVE
print(f"Saving SVM model to {MODEL_DIR}...")
with open(MODEL_DIR / 'eisenhower_model.pkl', 'wb') as f:
    pickle.dump(model, f)
with open(MODEL_DIR / 'tfidf_vectorizer.pkl', 'wb') as f:
    pickle.dump(vectorizer, f)

print("Training Complete! Beeware is now a General Productivity Tool.") 