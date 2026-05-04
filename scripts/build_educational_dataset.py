
import json
import subprocess
import pandas as pd
import os

os.makedirs('data/processed', exist_ok=True)

print("Extracting 100 Educational titles from COIN...")
with open('data/raw/COIN/COIN.json', 'r') as f:
    coin_data = json.load(f)['database']

educational_samples = []
count = 0
for vid_id in coin_data.keys():
    if count >= 100:
        break
    url = f"https://www.youtube.com/watch?v={vid_id}"
    try:
        title = subprocess.check_output(['yt-dlp', '--get-title', url], stderr=subprocess.DEVNULL).decode('utf-8').strip()
        educational_samples.append({'title': title, 'content_type': 'Educational'})
        print(f"[{count+1}/100] Fetched: {title[:50]}")
        count += 1
    except Exception:
        continue

df_educational = pd.DataFrame(educational_samples)
df_distractions = pd.read_csv('data/raw/most_viewed_videos_1000.csv')[['title', 'content_type']]

df_combined = pd.concat([df_distractions, df_educational], ignore_index=True)
df_combined.to_csv('data/processed/youtube_training_data.csv', index=False)

print("Success! Saved to data/processed/youtube_training_data.csv")