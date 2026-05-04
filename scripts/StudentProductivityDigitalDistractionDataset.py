import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import pickle

df = pd.read_csv('student_productivity_distraction_dataset_20000.csv')

# --- FIX 1: THE CORRECT FEATURE ORDER ---
# Must match the CSV exactly as you printed it
features = ['study_hours_per_day', 'phone_usage_hours', 'social_media_hours', 'gaming_hours']

# --- FIX 2: RE-CALIBRATE PRODUCTIVITY ---
# Instead of a hard '70', let's use the average of your actual data
median_score = df['productivity_score'].median()
print(f"Median Productivity Score in data: {median_score}")
df['is_productive'] = np.where(df['productivity_score'] > median_score, 1, 0)

X = df[features]
y = df['is_productive']

# --- TRAIN ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
model.fit(X_train, y_train)

# --- SAVE ---
with open('beeware_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("AI Re-trained and Saved with corrected logic!")