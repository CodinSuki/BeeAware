import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA = BASE_DIR / 'data' / 'raw'
OUTPUT_DIR = BASE_DIR / 'data' / 'processed'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

input_csv = RAW_DATA / 'steam.csv'
output_csv = OUTPUT_DIR / 'beeaware_steam_mapped.csv'

print(f"Loading raw Steam data from {input_csv}...")

try:
    df_steam = pd.read_csv(input_csv)
    
    growth_tags = [
        'Education', 'Software', 'Utilities', 'Design & Illustration', 
        'Web Publishing', 'Video Production', 'Audio Production', 
        'Animation & Modeling', 'Game Development', 'Software Training'
    ]
    pattern = '|'.join(growth_tags)

    print("Analyzing SteamSpy Tags...")
    df_steam['steamspy_tags'] = df_steam['steamspy_tags'].fillna('')
    is_growth = df_steam['steamspy_tags'].str.contains(pattern, case=False, regex=True)


    steam_q1_raw = df_steam[is_growth].copy()
    steam_q3_raw = df_steam[~is_growth].copy()


    steam_q1_data = pd.DataFrame({
        'window_title': steam_q1_raw['name'].astype(str) + " - App",
        'quadrant': 1  
    })

    steam_q3_data = pd.DataFrame({
        'window_title': steam_q3_raw['name'].astype(str) + " - App",
        'quadrant': 3  
    })


    steam_q3_data = steam_q3_data.sample(n=min(3000, len(steam_q3_data)), random_state=42)

    final_steam_data = pd.concat([steam_q1_data, steam_q3_data], ignore_index=True)
    final_steam_data = final_steam_data.dropna()
    final_steam_data.to_csv(output_csv, index=False)

    print("\n--- PROCESSING COMPLETE ---")
    print(f"Found {len(steam_q1_data)} Growth/Edu tools (Mapped to 1)")
    print(f"Sampled {len(steam_q3_data)} Standard Games (Mapped to 3)")
    print(f"Saved clean file to: {output_csv}")

except FileNotFoundError:
    print(f"ERROR: Could not find {input_csv}")