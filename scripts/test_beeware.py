import pickle
import pandas as pd
import numpy as np


try:
    with open('beeware_model.pkl', 'rb') as f:
        model = pickle.load(f)
    print("--- Beeware AI Loaded Successfully ---")
except FileNotFoundError:
    print("Error: beeware_model.pkl not found! Run your training script first.")
    exit()

features = ['study_hours_per_day', 'phone_usage_hours', 'social_media_hours', 'gaming_hours']

scenarios = {
    "The Deep Worker": [8.0, 1.0, 0.5, 0.0],    # 8h Study, 1h Phone, 0.5h Social, 0h Game
    "The Procrastinator": [1.0, 6.0, 4.0, 5.0], # 1h Study, 6h Phone, 4h Social, 5h Game
    "The Balanced Student": [4.0, 2.0, 1.0, 1.0] # 4h Study, 2h Phone, 1h Social, 1h Game
}

print(f"{'Scenario':<20} | {'Prediction':<15} | {'Confidence'}")
print("-" * 55)


for name, data in scenarios.items():
   
    df_input = pd.DataFrame([data], columns=features)
    
    prediction = model.predict(df_input)[0]
    probability = model.predict_proba(df_input)[0]
    
    
    confidence = probability[1] if prediction == 1 else probability[0]
    result_text = "Productive" if prediction == 1 else "Distracted"
    
    print(f"{name:<20} | {result_text:<15} | {confidence:.2%}")