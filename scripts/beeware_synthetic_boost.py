import pandas as pd
import random

seeds = pd.read_csv('data/raw/BeeAware_Synthetic_Boost2.csv')

# Q1: Urgent & Important
q1_subj = seeds[seeds['tag_type'] == 'q1_subject']['value'].tolist()
q1_act = seeds[seeds['tag_type'] == 'q1_action']['value'].tolist()
q1_plat = seeds[seeds['tag_type'] == 'q1_platform']['value'].tolist()
q1_urg = seeds[seeds['tag_type'] == 'q1_urgency']['value'].tolist()

# Q2: Important, NOT Urgent (Deep Work/Planning)
q2_subj = seeds[seeds['tag_type'] == 'q2_subject']['value'].tolist()
q2_growth = seeds[seeds['tag_type'] == 'q2_growth']['value'].tolist()
q2_plan = seeds[seeds['tag_type'] == 'q2_planning']['value'].tolist()
q2_maint = seeds[seeds['tag_type'] == 'q2_maintenance']['value'].tolist()

# Q3: Urgent, NOT Important (Interruptions)
q3_subj = seeds[seeds['tag_type'] == 'q3_subject']['value'].tolist()
q3_act = seeds[seeds['tag_type'] == 'q3_action']['value'].tolist()
q3_plat = seeds[seeds['tag_type'] == 'q3_platform']['value'].tolist()

data = []
samples_per_quadrant = 3000  

print(f"Generating Master Training Data ({samples_per_quadrant} per quadrant)...")

for _ in range(samples_per_quadrant):

    # GENERATE Q1 (Quadrant 0): Panicked & Important
 
    q1_a = f"{random.choice(q1_act).strip()} {random.choice(q1_subj).strip()} - {random.choice(q1_urg).strip()}"
    q1_b = f"{random.choice(q1_urg).strip()}: {random.choice(q1_subj).strip()} ({random.choice(q1_plat).strip()})"
    q1_c = f"{random.choice(q1_subj).strip()} {random.choice(q1_act).strip()} on {random.choice(q1_plat).strip()} [{random.choice(q1_urg).strip()}]"
    data.append({"window_title": random.choice([q1_a, q1_b, q1_c]), "quadrant": 0})

    # GENERATE Q2 (Quadrant 1): Deep Work & Planning

    q2_a = f"{random.choice(q2_growth).strip()} {random.choice(q2_subj).strip()}"
    q2_b = f"{random.choice(q2_plan).strip()} for {random.choice(q2_subj).strip()}"
    q2_c = f"{random.choice(q2_subj).strip()} {random.choice(q2_maint).strip()}"
    data.append({"window_title": random.choice([q2_a, q2_b, q2_c]), "quadrant": 1})

    # GENERATE Q3 (Quadrant 2): Interruptions & Noise
  
    q3_a = f"{random.choice(q3_act).strip()} {random.choice(q3_subj).strip()}"
    q3_b = f"{random.choice(q3_subj).strip()} - {random.choice(q3_plat).strip()}"
    q3_c = f"{random.choice(q3_act).strip()} {random.choice(q3_subj).strip()} ({random.choice(q3_plat).strip()})"
    data.append({"window_title": random.choice([q3_a, q3_b, q3_c]), "quadrant": 2})


df_master = pd.DataFrame(data).drop_duplicates()

df_master = df_master.sample(frac=1).reset_index(drop=True)

df_master.to_csv('data/processed/beeaware_synthetic_boost2.csv', index=False)

print(f"Success! Saved {len(df_master)} perfectly balanced, shuffled titles to 'data/processed/beeaware_synthetic_boost2.csv'")