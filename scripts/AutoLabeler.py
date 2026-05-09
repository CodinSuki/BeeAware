import pandas as pd
import os


domains_df = pd.read_csv('data/raw/domains-top-500.csv')

KNOWN_DISTRACTIONS = ['facebook', 'instagram', 'tiktok', 'netflix', 'twitch', 'reddit', 'twitter', 'x.com', 'pinterest', 'spotify', 'roblox']
KNOWN_STUDY = ['github', 'stackoverflow', 'wikipedia', 'instructure', 'canvas', 'zoom', 'microsoft', 'google']

def auto_label_domain(domain_string):
    domain = str(domain_string).lower()

    if domain.endswith('.edu') or domain.endswith('.gov') or domain.endswith('.ac.uk'):
        return 1 # Study
        
  
    if any(study_site in domain for study_site in KNOWN_STUDY):
        return 1 # Study
        

    if any(distract_site in domain for distract_site in KNOWN_DISTRACTIONS):
        return 0 # Distraction
        

    return -1 # Unknown


domains_df['label'] = domains_df['domain'].apply(auto_label_domain)


os.makedirs('data/processed', exist_ok=True)
domains_df.to_csv('data/processed/domain_reference.csv', index=False)


study_count = len(domains_df[domains_df['label'] == 1])
distract_count = len(domains_df[domains_df['label'] == 0])
unknown_count = len(domains_df[domains_df['label'] == -1])

print(f"--- DOMAIN LABELING COMPLETE ---")
print(f"Study Domains Found: {study_count}")
print(f"Distraction Domains Found: {distract_count}")
print(f"Sent to AI (Unknown): {unknown_count}")
print("Saved to data/processed/domain_reference.csv")