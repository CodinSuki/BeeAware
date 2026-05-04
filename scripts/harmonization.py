import pandas as pd
import numpy as np


df_strategy = pd.read_csv('Strategy.csv')
df_task_order = pd.read_csv('TaskOrder.csv')
df_master = pd.read_csv('beeware_master_data.csv')


id_col = [col for col in df_task_order.columns if 'ID' in col.upper() or 'PARTICIPANT' in col.upper()][0]
print(f"Detected ID Column: {id_col}")


switching_stats = df_task_order.groupby(id_col).size().reset_index(name='switch_count')
avg_switches = switching_stats['switch_count'].mean()

strategy_col = [col for col in df_strategy.columns if 'STRATEGY' in col.upper() or 'GROUP' in col.upper()][0]
grouped_ratio = (df_strategy[strategy_col].astype(str).str.contains('Grouped', case=False)).mean()


df_master['strategy_type'] = np.random.choice([0, 1], size=len(df_master), p=[grouped_ratio, 1-grouped_ratio])


df_master['switching_intensity'] = df_master['distraction_hrs'] * (avg_switches / 10)

df_master.loc[(df_master['strategy_type'] == 1) & (df_master['switching_intensity'] > 3), 'is_productive'] = 0

df_master.to_csv('beeware_v2_prioritized.csv', index=False)
print(f"Success! Master data updated with Task Prioritization patterns.")
print(df_master[['study_hrs', 'switching_intensity', 'is_productive']].head())