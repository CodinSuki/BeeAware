import pandas as pd
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA = BASE_DIR / 'data' / 'raw'
OUTPUT_DIR = BASE_DIR / 'data' / 'processed'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

master_output_path = OUTPUT_DIR / 'beeware_master_training.csv'
booster_path = OUTPUT_DIR / 'beeware_synthetic_boost.csv'

def clean_url(url):
    if pd.isna(url): return "Unknown Browser"
    domain = url.split('//')[-1].split('/')[0].replace('www.', '')
    return f"{domain.capitalize()} - Browser"

# --- Source 1: Steam ---
print("Processing Steam.csv...")
df_steam = pd.read_csv(RAW_DATA / 'Steam.csv')
steam_data = pd.DataFrame({'window_title': df_steam['name'], 'quadrant': 3})

# --- Source 2: Web Classification ---
print("Processing website_classification.csv...")
df_web = pd.read_csv(RAW_DATA / 'website_classification.csv')
web_map = {'Education': 1, 'Business': 1, 'Social Networking': 3, 'Entertainment': 3, 'Streaming': 3}
web_data = pd.DataFrame({
    'window_title': df_web['website_url'].apply(clean_url),
    'quadrant': df_web['Category'].map(web_map)
})

# --- Source 3: Distracting Sites ---
print("Processing Distracting-Websites text files...")
distract_path = RAW_DATA / 'Distracting-Websites' / 'lists'
txt_results = []
for folder in ['Games', 'Entertainment', 'Social']:
    path = distract_path / folder
    if path.exists():
        for txt_file in path.glob('*.txt'):
            with open(txt_file, 'r', encoding='utf-8') as f:
                domains = [line.strip() for line in f if line.strip()]
                for d in domains:
                    txt_results.append({'window_title': f"{d.capitalize()} - Browser", 'quadrant': 3})
txt_data = pd.DataFrame(txt_results)

# --- Source 4: The Synthetic Booster (CRITICAL CHECK) ---
if booster_path.exists():
    print(f"SUCCESS: Found booster at {booster_path}. Loading 3,000 samples...")
    df_boost = pd.read_csv(booster_path)
else:
    print(f"ERROR: Could not find {booster_path}! Check your folders.")
    df_boost = pd.DataFrame(columns=['window_title', 'quadrant'])

# --- Source 5: Manual Project Data ---
manual_data = pd.DataFrame([
    {'window_title': 'Beeware - Visual Studio Code', 'quadrant': 1},
    {'window_title': 'ESP32 Microprocessor Documentation', 'quadrant': 1},
    {'window_title': '8086 Assembly - VS Code', 'quadrant': 1},
    {'window_title': 'Discord', 'quadrant': 2},
    {'window_title': 'Messenger', 'quadrant': 2}
])

# ==========================================
# 6. FINAL CONSOLIDATION
# ==========================================
master_df = pd.concat([steam_data, web_data, txt_data, df_boost, manual_data], ignore_index=True)

# Clean and save
master_df = master_df.dropna(subset=['quadrant'])
master_df = master_df.drop_duplicates(subset=['window_title'])
master_df.to_csv(master_output_path, index=False)

print(f"\n--- Final Verification ---")
print(f"Total Unique Titles: {len(master_df)}")
print(master_df['quadrant'].value_counts())