import pandas as pd
import os

# 1. Load your Top 500 Domains
domains_df = pd.read_csv('data/raw/domains-top-500.csv')

# 2. Define our "Rule of Thumb" Lists
# These are the most common culprits in the Top 500
KNOWN_DISTRACTIONS = ['facebook', 'instagram', 'tiktok', 'netflix', 'twitch', 'reddit', 'twitter', 'x.com', 'pinterest', 'spotify', 'roblox']
KNOWN_STUDY = ['github', 'stackoverflow', 'wikipedia', 'instructure', 'canvas', 'zoom', 'microsoft', 'google']

def auto_label_domain(domain_string):
    domain = str(domain_string).lower()
    
    # Rule 1: The "Free Pass" Educational Domains
    if domain.endswith('.edu') or domain.endswith('.gov') or domain.endswith('.ac.uk'):
        return 1 # Study
        
    # Rule 2: Check against known study tools
    if any(study_site in domain for study_site in KNOWN_STUDY):
        return 1 # Study
        
    # Rule 3: Check against known distractions
    if any(distract_site in domain for distract_site in KNOWN_DISTRACTIONS):
        return 0 # Distraction
        
    # Rule 4: Let the Tier 2 AI handle the rest!
    return -1 # Unknown

# 3. Apply the rules to the dataset
# Assuming the column containing the website is called 'domain'
# If it's called something else, change 'domain' below to match your CSV
domains_df['label'] = domains_df['domain'].apply(auto_label_domain)

# 4. Save the final reference file for Beeware
os.makedirs('data/processed', exist_ok=True)
domains_df.to_csv('data/processed/domain_reference.csv', index=False)

# Let's see the results!
study_count = len(domains_df[domains_df['label'] == 1])
distract_count = len(domains_df[domains_df['label'] == 0])
unknown_count = len(domains_df[domains_df['label'] == -1])

print(f"--- DOMAIN LABELING COMPLETE ---")
print(f"Study Domains Found: {study_count}")
print(f"Distraction Domains Found: {distract_count}")
print(f"Sent to AI (Unknown): {unknown_count}")
print("Saved to data/processed/domain_reference.csv")