import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA = BASE_DIR / 'data' / 'raw'
OUTPUT_DIR = BASE_DIR / 'data' / 'processed'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

input_csv = RAW_DATA / 'windows_apps_games_stats.csv'  
output_csv = OUTPUT_DIR / 'beeaware_real_apps_mapped.csv'

print(f"Loading raw Kaggle data from {input_csv}...")

try:
    df_apps = pd.read_csv(input_csv)
 
    category_map = {
        'Productivity': 1, 
        'Education': 1,
        'Business': 1,
        'Developer Tools': 1,
        'Utilities & tools': 1, 
        'Medical': 1,
        'Health & fitness': 1,
        
        'Social': 2,
        'Communication': 2, 
        
        'Games': 3, 
        'Entertainment': 3,
        'Music': 3,
        'Video': 3,
        'Lifestyle': 3,
        'Sports': 3,
        'Shopping': 3
    }

    print("Cleaning version numbers and Mapping Categories to Quadrants...")
    
  
    cleaned_app_names = df_apps['app_name'].astype(str).str.replace(r'\s*[vV]\d+$', '', regex=True)

    mapped_data = pd.DataFrame({
        'window_title': cleaned_app_names + " - App",
        'quadrant': df_apps['category'].map(category_map)
    })

    initial_count = len(mapped_data)
 
    mapped_data = mapped_data.dropna(subset=['quadrant'])
    mapped_data['quadrant'] = mapped_data['quadrant'].astype(int)
    
 
 
    mapped_data = mapped_data.drop_duplicates(subset=['window_title'])
    
    final_count = len(mapped_data)

    mapped_data.to_csv(output_csv, index=False)
    
    print("\n--- PROCESSING COMPLETE ---")
    print(f"Original Apps in CSV: {initial_count}")
    print(f"Successfully Mapped (Unique): {final_count}")
    print(f"Dropped {initial_count - final_count} unmapped or duplicate apps.")
    print(f"\nBreakdown by Quadrant:")
    print(mapped_data['quadrant'].value_counts().sort_index())
    print(f"\nSaved ready-to-train file to: {output_csv}")

except FileNotFoundError:
    print(f"\nERROR: Could not find the file at {input_csv}.")
    print("Please make sure you downloaded the Kaggle CSV and placed it in your data/raw folder!")
except KeyError as e:
    print(f"\nERROR: Column mismatch. The Kaggle CSV might use different column names.")
    print(f"Missing column: {e}. Open the CSV in Excel to check the exact header names (e.g., 'Name' instead of 'App Name').")