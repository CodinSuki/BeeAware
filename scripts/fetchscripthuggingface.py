from huggingface_hub import hf_hub_download
import os

# Ensure your directory exists
os.makedirs('data/raw', exist_ok=True)

# Download the file
path = hf_hub_download(
    repo_id="commoncrawl/statistics", 
    filename="domains-top-500.csv", 
    repo_type="dataset",
    local_dir="data/raw"
)

print(f"File downloaded to: {path}")