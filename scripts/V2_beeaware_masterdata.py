import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA = BASE_DIR / 'data' / 'raw'
OUTPUT_DIR = BASE_DIR / 'data' / 'processed'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

master_output_path = OUTPUT_DIR / 'V2beeware_master_training.csv'

ROW_CAP = 3000
IMBALANCE_THRESHOLD = 2.0


def clean_url(url: str) -> str:
    if pd.isna(url):
        return "Unknown Browser"
    domain = url.split('//')[-1].split('/')[0]
    for prefix in ('www.', 'm.', 'mobile.'):
        if domain.lower().startswith(prefix):
            domain = domain[len(prefix):]
    return f"{domain.capitalize()} - Browser"


def safe_load_csv(path: Path, required_cols: list[str]) -> pd.DataFrame:
    if not path.exists():
        print(f"  Warning: {path.name} not found, skipping.")
        return pd.DataFrame(columns=required_cols)

    df = pd.read_csv(path)

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"  Error: {path.name} is missing columns: {missing}")
        print(f"  Found columns: {list(df.columns)}")
        return pd.DataFrame(columns=required_cols)

    return df


def cap(df: pd.DataFrame, n: int = ROW_CAP, label: str = "") -> pd.DataFrame:
    before = len(df)
    result = df.sample(n=min(n, before), random_state=42)
    if before > n:
        print(f"  Capped {label}: {before} -> {n} rows")
    else:
        print(f"  {label}: {before} rows (under cap, keeping all)")
    return result


def check_balance(df: pd.DataFrame) -> None:
    counts = df['quadrant'].value_counts().sort_index()
    print("\n--- Quadrant Breakdown ---")
    for q, n in counts.items():
        print(f"  Q{q}: {n:>5} rows")

    min_n = counts.min()
    max_n = counts.max()
    ratio = max_n / min_n if min_n > 0 else float('inf')

    if ratio > IMBALANCE_THRESHOLD:
        print(
            f"\n  IMBALANCE WARNING: largest quadrant ({max_n}) is "
            f"{ratio:.1f}x the smallest ({min_n}).\n"
            f"  Consider capping or upsampling before training.\n"
            f"  Rebalancing target: ~{min_n} rows each."
        )
    else:
        print(f"\n  Balance OK (ratio {ratio:.1f}x)")


def detect_label_conflicts(df: pd.DataFrame) -> None:
    conflicts = (
        df.groupby('window_title')['quadrant']
        .nunique()
        .loc[lambda s: s > 1]
    )
    if conflicts.empty:
        print("  No label conflicts detected")
        return

    print(f"\n  {len(conflicts)} window title(s) have conflicting quadrant labels:")
    for title in conflicts.index[:10].tolist():
        labels = sorted(df.loc[df['window_title'] == title, 'quadrant'].unique())
        print(f"    '{title}' -> quadrants {labels}")
    if len(conflicts) > 10:
        print(f"    ... and {len(conflicts) - 10} more. Fix these in your source files.")


# 1. Steam data
print("\n[1/6] Loading mapped Steam data...")
steam_data = safe_load_csv(
    OUTPUT_DIR / 'beeaware_steam_mapped.csv',
    required_cols=['window_title', 'quadrant']
)
steam_data = cap(steam_data, label="Steam")


# 2. Website classification CSV
print("\n[2/6] Processing website_classification.csv...")

web_map = {
    'Education':         1,
    'Business':          1,
    'Finance':           1,
    'Health':            1,
    'Reference':         1,
    'Science':           1,
    'Social Networking': 2,
    'News':              2,
    'Forums':            2,
    'Shopping':          2,
    'Entertainment':     3,
    'Streaming':         3,
    'Adult':             3,
    'Games':             3,
}

df_web_raw = pd.read_csv(RAW_DATA / 'website_classification.csv')

unmapped = set(df_web_raw['Category'].dropna().unique()) - set(web_map.keys())
if unmapped:
    print(f"  Unmapped web categories (rows will be dropped): {unmapped}")

web_data = pd.DataFrame({
    'window_title': df_web_raw['website_url'].apply(clean_url),
    'quadrant':     df_web_raw['Category'].map(web_map),
}).dropna()

web_data = cap(web_data, label="Web CSV")


# 3. Distracting-Websites text files
print("\n[3/6] Processing Distracting-Websites text files...")
distract_path = RAW_DATA / 'Distracting-Websites' / 'lists'
txt_results = []

for folder in ['Games', 'Entertainment', 'Social']:
    path = distract_path / folder
    if path.exists():
        for txt_file in path.glob('*.txt'):
            with open(txt_file, 'r', encoding='utf-8') as f:
                domains = [line.strip() for line in f if line.strip()]
                for d in domains:
                    txt_results.append({
                        'window_title': f"{d.capitalize()} - Browser",
                        'quadrant': 4,
                    })
    else:
        print(f"  Folder not found: {path}")

txt_data = pd.DataFrame(txt_results)
txt_data = cap(txt_data, label="Txt files")


# 4. Kaggle mapped apps
print("\n[4/6] Loading Kaggle mapped apps...")
mapped_apps = safe_load_csv(
    OUTPUT_DIR / 'beeaware_real_apps_mapped.csv',
    required_cols=['window_title', 'quadrant']
)
mapped_apps = cap(mapped_apps, label="Kaggle apps")


# 5. Synthetic boosters
print("\n[5/6] Gathering Synthetic Boosters...")
booster_files = [
    'beeaware_synthetic_boost.csv',
    'beeaware_synthetic_boost2.csv',
    'beeaware_keyword_boost.csv',
]

boost_dfs = []
for file_name in booster_files:
    file_path = OUTPUT_DIR / file_name
    if file_path.exists():
        df_b = pd.read_csv(file_path)
        print(f"  Loaded {file_name}: {len(df_b)} rows")
        boost_dfs.append(df_b)
    else:
        print(f"  Not found: {file_name}")

df_all_boosts = (
    pd.concat(boost_dfs, ignore_index=True)
    if boost_dfs
    else pd.DataFrame(columns=['window_title', 'quadrant'])
)

# Merge
print("\nMerging all datasets...")

master_df = pd.concat(
    [steam_data, web_data, txt_data, mapped_apps, df_all_boosts],
    ignore_index=True,
)

master_df = master_df.dropna(subset=['quadrant', 'window_title'])
master_df['quadrant'] = master_df['quadrant'].astype(int)

print("\nChecking for label conflicts...")
detect_label_conflicts(master_df)

master_df = master_df.drop_duplicates(subset=['window_title'])


# Balance check and save
check_balance(master_df)

master_df.to_csv(master_output_path, index=False)

print(f"\n{'─' * 50}")
print(f"Total unique titles : {len(master_df)}")
print(f"Saved to            : {master_output_path}")
print(f"{'─' * 50}")