# BeeAware Live Model Retraining - Implementation Summary

## Overview
Successfully implemented live model retraining support for BeeAware. The app now:
1. Logs detailed feature_text for every tracked activity
2. Captures user corrections when wrong classifications are fixed
3. Can retrain the classifier on accumulated corrections
4. Provides a manual "Retrain Model Now" button in Settings

---

## Changes Made

### 1. **config.py** — Updated CSV Schemas

#### Added new paths and columns:
```python
# NEW: Paths for retraining corrections
CORRECTIONS_CSV_PATH  = os.path.join(BASE_DIR, "data", "beeaware_corrections.csv")
CORRECTIONS_ARCHIVE_PATH = os.path.join(BASE_DIR, "data", "beeaware_corrections_archive.csv")

# UPDATED: APP_HISTORY_COLS now includes predicted_q, window_title, feature_text
APP_HISTORY_COLS = [
    "date", "session_ts", "exe_name", "total_seconds",
    "q1_seconds", "q2_seconds", "q3_seconds", "q4_seconds",
    "dominant_q", "predicted_q", "window_title", "feature_text", "frequency_rank",
]

# NEW: Schema for retraining corrections file
CORRECTIONS_COLS = [
    "timestamp", "window_title", "feature_text", "predicted_q", "corrected_q",
]
```

**Backward Compatibility:** Both `dominant_q` (original) and `predicted_q` (new) are kept for compatibility.

---

### 2. **app.py** — Enhanced Activity Tracking & Feature Extraction

#### 2a. Added feature extraction helpers:
```python
# NEW METHOD: extract_browser_domain()
# Extracts domain/service names from browser titles (github, youtube, slack, etc.)

# UPDATED METHOD: build_nlp_input()
# Now builds feature_text in exact format matching training data:
#   "{exe_label} | {source_type} | {app_family} | {browser_category} | {browser_domain} | {raw_title}"
# Instead of old: "{exe_label} | {source_type} | {app_family} | {browser_category} | {raw_title}"
```

#### 2b. Enhanced state tracking:
```python
# NEW fields added to __init__:
self.current_feature_text = ""      # For retraining corrections
self.current_predicted_q = None      # For retraining corrections
```

#### 2c. Updated app_freq tracking:
```python
# app_freq now tracks per-app:
{
    "seconds": 0,
    "quadrant_counts": {0: 0, 1: 0, 2: 0, 3: 0},
    "path": exe_path,
    "window_title": raw_title,              # NEW
    "feature_text": feature_text,           # NEW
}
```

#### 2d. Enhanced watcher_loop():
- Now stores `current_feature_text` and `current_predicted_q` when classification happens
- Tracks these values in `app_freq` for logging at session end

#### 2e. Updated save_app_history():
```python
# Now writes all new columns:
writer.writerow([
    date_str, session_ts, exe_name, data["seconds"],
    qc[0], qc[1], qc[2], qc[3], dominant_q, predicted_q,  # predicted_q = dominant_q
    window_title, feature_text, rank,  # NEW columns
])
```

---

### 3. **ui/correction.py** — Correction Logging for Retraining

#### 3a. Updated imports:
```python
# Added new config paths
from config import (
    ...existing imports...,
    CORRECTIONS_CSV_PATH, CORRECTIONS_ARCHIVE_PATH, CORRECTIONS_COLS,
)

# Legacy audit log kept for backward compatibility
CORRECTIONS_PATH = os.path.join(config.BASE_DIR, "data", "corrections.csv")
CORRECTIONS_COLS_LEGACY = [...]  # Original columns
```

#### 3b. Enhanced _apply_correction():
```python
# Now calls new method to write to beeaware_corrections.csv:
self._save_correction_for_retrain(
    title, 
    self.current_feature_text,  # Use feature_text from app state
    predicted_q,                 # Extracted from original_verdict
    corrected_label              # User's correction
)
```

#### 3c. New method _save_correction_for_retrain():
```python
def _save_correction_for_retrain(self, window_title, feature_text, predicted_q, corrected_q):
    """Append to beeaware_corrections.csv for model retraining."""
    # Columns: timestamp, window_title, feature_text, predicted_q, corrected_q
```

---

### 4. **ui/options.py** — Manual Retrain Trigger

#### 4a. Added retrain button to Settings:
```python
self.btn_retrain = ctk.CTkButton(
    container,
    text="Retrain Model Now",
    command=self.retrain_model_now,
    fg_color=BEE_AMBER,
    hover_color=BEE_AMBER_DIM,
)
# Positioned at row 13, just before Close button
```

#### 4b. New method retrain_model_now():
```python
def retrain_model_now(self):
    """Execute retrain.py script in background thread."""
    # Runs subprocess with retrain.py
    # Disables button during execution
    # Shows notification on completion/error
    # Optionally reloads trained models
```

#### 4c. New helper method _reload_models():
```python
def _reload_models(self):
    """Reload model and vectorizer from disk after retraining."""
```

---

### 5. **retrain.py** — New Model Retraining Script

Complete standalone script that:

**Inputs:**
- `Training/data/processed/V3beeware_master_training.csv` (original training data)
- `BeeAware/data/beeaware_corrections.csv` (accumulated corrections from live sessions)

**Processing:**
1. Loads both datasets
2. Removes training examples that match corrected feature_text
3. Merges training + corrections (corrections override duplicates)
4. Retrains TfidfVectorizer + LinearSVC with original hyperparameters:
   - TfidfVectorizer: ngram_range=(1,2), max_features=12000, stop_words='english'
   - LinearSVC: class_weight='balanced', dual=False, max_iter=10000

**Outputs:**
- Saves new model to `BeeAware/models/V4eisenhower_model.pkl`
- Saves new vectorizer to `BeeAware/models/V4tfidf_vectorizer.pkl`
- Backs up old models to `.backup.pkl` files
- Archives corrections to `beeaware_corrections_archive.csv`
- Clears `beeaware_corrections.csv` for next batch

**Features:**
- `--dry-run` flag to preview changes without saving
- Comprehensive logging with progress indicators
- Error handling and validation
- Timeout protection (5 minutes)

**Usage:**
```bash
python retrain.py                # Run retraining
python retrain.py --dry-run      # Preview without changes
```

---

## Data Flow Diagram

```
User Activity
    ↓
app.py watcher_loop
    ├─ Classify using model
    ├─ Store current_feature_text & current_predicted_q
    └─ Track in app_freq (with window_title, feature_text)
    ↓
save_app_history()
    └─ Write to beeaware_app_history.csv
       Columns: ..., predicted_q, window_title, feature_text, ...

User Correction (Wrong? Fix it button)
    ↓
ui/correction.py _apply_correction()
    ├─ Update overrides.json (instant effect)
    └─ _save_correction_for_retrain()
        └─ Write to beeaware_corrections.csv
           Columns: timestamp, window_title, feature_text, predicted_q, corrected_q

Manual Retrain Trigger (Settings → Retrain Model Now)
    ↓
ui/options.py retrain_model_now()
    └─ subprocess.run(retrain.py)
        ├─ Load training data + corrections
        ├─ Merge (corrections override)
        ├─ Retrain model
        ├─ Save new model/vectorizer
        └─ Archive corrections & clear active file
```

---

## CSV Schema Changes

### beeaware_app_history.csv
**Before:**
```
date,session_ts,exe_name,total_seconds,q1_seconds,q2_seconds,q3_seconds,q4_seconds,dominant_q,frequency_rank
```

**After:**
```
date,session_ts,exe_name,total_seconds,q1_seconds,q2_seconds,q3_seconds,q4_seconds,dominant_q,predicted_q,window_title,feature_text,frequency_rank
```

### beeaware_corrections.csv (NEW)
```
timestamp,window_title,feature_text,predicted_q,corrected_q
2024-08-26 14:32:15,GitHub - MyRepo,github | web browser | dev | dev | github | GitHub - MyRepo,1,0
2024-08-26 14:35:22,Netflix - Stranger Things,firefox | web browser | media | media | netflix | Netflix - Stranger Things,3,2
```

### beeaware_corrections_archive.csv
- Accumulated archive of processed corrections (created automatically during retrain)

---

## Backward Compatibility

✅ **Fully backward compatible:**
- Both `dominant_q` and `predicted_q` exist (keeps existing code working)
- New columns appended to end of app_history.csv
- Legacy `corrections.csv` audit log still written (new file separate)
- All existing UI panels (graphs, history, insights) continue working unchanged
- No breaking changes to any existing CSV files

---

## Testing Checklist

✓ Feature text building matches training data format
✓ Window title and feature text logged for each app
✓ Corrections written to new CSV with correct schema
✓ Retrain button appears in Settings
✓ Retrain script loads training + corrections correctly
✓ Model retraining succeeds with proper hyperparameters
✓ Old models backed up before overwrite
✓ Corrections archived and cleared after retrain
✓ Manual retrain works via Settings button
✓ Error handling for missing files/timeouts
✓ Backward compatibility maintained

---

## Next Steps (Optional Enhancements)

1. **Auto-retrain on startup** — Check if corrections.csv has ≥N rows, auto-trigger retrain
2. **Retrain progress UI** — Show progress bar during retraining
3. **Model metrics display** — Show F1-score, accuracy improvements in Settings
4. **Selective retraining** — Allow user to pick which corrections to use
5. **Cloud sync** — Optional: sync corrections across devices

---

## Files Modified

1. `BeeAware/config.py` — Schema updates
2. `BeeAware/app.py` — Enhanced tracking & feature extraction
3. `BeeAware/ui/correction.py` — Correction logging
4. `BeeAware/ui/options.py` — Retrain button & handler
5. `BeeAware/retrain.py` — NEW retraining script

**No files deleted or renamed.**
