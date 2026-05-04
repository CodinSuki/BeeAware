import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import pickle

# 1. LOAD THE HARMONIZED DATA
df = pd.read_csv('beeware_master_data.csv')

# 2. SELECT FEATURES
# These are the columns we standardized in Phase 1
features = ['study_hrs', 'distraction_hrs', 'sleep_hrs', 'stress_level']
X = df[features]
y = df['is_productive']

# 3. SPLIT DATA
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. TRAIN THE MODEL
# We're using a slightly deeper forest to handle the new health patterns
model = RandomForestClassifier(n_estimators=150, max_depth=12, random_state=42)
model.fit(X_train, y_train)

# 5. EVALUATE
y_pred = model.predict(X_test)
print("--- Super-Model Performance ---")
print(f"Accuracy: {accuracy_score(y_test, y_pred):.2%}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# 6. SAVE THE SUPER-BRAIN
with open('beeware_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("\nPhase 2 Complete: beeware_model.pkl has been upgraded!")