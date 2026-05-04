import pandas as pd
import random


work_categories = ["Project", "Document", "Report", "Research", "Task", "Assignment"]
urgent_tags = ["Deadline", "Final Version", "Urgent", "Priority", "Immediate Action"]
growth_tags = ["Tutorial", "Learning", "Deep Work", "Drafting", "Planning", "Guide"]
noise_tags = ["Notification", "Alert", "Incoming Call", "New Message", "System Update"]

data = []


for i in range(1500):

    data.append({"window_title": f"{random.choice(work_categories)} {random.choice(urgent_tags)}", "quadrant": 0})

    data.append({"window_title": f"{random.choice(work_categories)} {random.choice(growth_tags)}", "quadrant": 1})
    

    data.append({"window_title": f"{random.choice(noise_tags)}", "quadrant": 2})

df_boost = pd.DataFrame(data)
df_boost.to_csv('data/processed/beeware_synthetic_boost.csv', index=False)
print("Generalized synthetic data generated.")