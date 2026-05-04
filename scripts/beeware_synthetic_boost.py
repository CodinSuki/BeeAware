import pandas as pd
import random

# Generalized categories for any user
work_categories = ["Project", "Document", "Report", "Research", "Task", "Assignment"]
urgent_tags = ["Deadline", "Final Version", "Urgent", "Priority", "Immediate Action"]
growth_tags = ["Tutorial", "Learning", "Deep Work", "Drafting", "Planning", "Guide"]
noise_tags = ["Notification", "Alert", "Incoming Call", "New Message", "System Update"]

data = []

# Generate 1500 unique samples per quadrant
for i in range(1500):
    # Q1: Urgent (0) - e.g., "Project Deadline"
    data.append({"window_title": f"{random.choice(work_categories)} {random.choice(urgent_tags)}", "quadrant": 0})
    
    # Q2: Growth (1) - e.g., "Research Guide"
    data.append({"window_title": f"{random.choice(work_categories)} {random.choice(growth_tags)}", "quadrant": 1})
    
    # Q3: Noise (2) - e.g., "New Message Notification"
    data.append({"window_title": f"{random.choice(noise_tags)}", "quadrant": 2})

df_boost = pd.DataFrame(data)
df_boost.to_csv('data/processed/beeware_synthetic_boost.csv', index=False)
print("Generalized synthetic data generated.")