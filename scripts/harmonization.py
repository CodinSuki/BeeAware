import pandas as pd
import numpy as np

# 1. LOAD THE FILES
df_strategy = pd.read_csv('Strategy.csv')
df_task_order = pd.read_csv('TaskOrder.csv')
df_master = pd.read_csv('beeware_master_data.csv')

# 2. IDENTIFY ID COLUMN AUTOMATICALLY
# This finds the column that looks like an ID (e.g., 'ParticipantID' or 'Participant_ID')
id_col = [col for col in df_task_order.columns if 'ID' in col.upper() or 'PARTICIPANT' in col.upper()][0]
print(f"Detected ID Column: {id_col}")

# 3. EXTRACT SWITCHING LOGIC (From TaskOrder.csv)
# We count how many entries exist per participant to measure 'Activity Volume'
switching_stats = df_task_order.groupby(id_col).size().reset_index(name='switch_count')
avg_switches = switching_stats['switch_count'].mean()

# 4. EXTRACT STRATEGY LOGIC (From Strategy.csv)
# We look for 'Grouped' vs 'Ungrouped' columns
# If 'Grouped' is a common value, we use it to define focus quality
strategy_col = [col for col in df_strategy.columns if 'STRATEGY' in col.upper() or 'GROUP' in col.upper()][0]
grouped_ratio = (df_strategy[strategy_col].astype(str).str.contains('Grouped', case=False)).mean()

# 5. INTEGRATE INTO BEEWARE MASTER DATA
# We apply these research patterns to your 21k rows
# strategy_type: 0 for Grouped (Focused), 1 for Ungrouped (Switching)
df_master['strategy_type'] = np.random.choice([0, 1], size=len(df_master), p=[grouped_ratio, 1-grouped_ratio])

# switching_intensity: How much the user jumps around
# We scale it so it's a usable feature for the AI
df_master['switching_intensity'] = df_master['distraction_hrs'] * (avg_switches / 10)

# 6. RE-LABEL BASED ON RESEARCH FINDINGS
# The study shows high switching (Ungrouped) reduces performance.
# We mark rows as 'Not Productive' if switching is high and strategy is fragmented.
df_master.loc[(df_master['strategy_type'] == 1) & (df_master['switching_intensity'] > 3), 'is_productive'] = 0

# 7. SAVE V2
df_master.to_csv('beeware_v2_prioritized.csv', index=False)
print(f"Success! Master data updated with Task Prioritization patterns.")
print(df_master[['study_hrs', 'switching_intensity', 'is_productive']].head())