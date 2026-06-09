import os
import sys
import json

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ERROR_LOG_PATH       = os.path.join(BASE_DIR, "data", "beeaware_errors.log")
DAILY_LOG_PATH       = os.path.join(BASE_DIR, "data", "beeaware_daily_log.csv")
APP_HISTORY_PATH     = os.path.join(BASE_DIR, "data", "beeaware_app_history.csv")
OVERRIDES_JSON_PATH  = os.path.join(BASE_DIR, "data", "overrides.json")
IDLE_EXCLUSIONS_PATH = os.path.join(BASE_DIR, "data", "idle_exclusions.json")
MODEL_PATH           = os.path.join(BASE_DIR, "models", "V4eisenhower_model.pkl")
VECTORIZER_PATH      = os.path.join(BASE_DIR, "models", "V4tfidf_vectorizer.pkl")

# Colours
BEE_AMBER      = "#c8922a"
BEE_AMBER_DIM  = "#a87820"
BEE_GOLD       = "#e8b84b"
BEE_COMB       = "#2e2416"
BEE_COMB_LIGHT = "#3a2e1a"
BEE_COMB_MID   = "#4a3b22"
BEE_BROWN      = "#6b4f2a"
BEE_CREAM      = "#d4b483"
BEE_GREEN      = "#7a9e6e"
BEE_RED        = "#b8604a"
BEE_GRAY       = "#7a6e5e"

QUADRANTS = {0: "Q1: URGENT", 1: "Q2: GROWTH", 2: "Q3: NOISE", 3: "Q4: PLAY"}
Q_COLORS  = {0: BEE_RED, 1: BEE_GREEN, 2: BEE_AMBER, 3: BEE_GOLD}

APP_HISTORY_COLS = [
    "date", "session_ts", "exe_name", "total_seconds",
    "q1_seconds", "q2_seconds", "q3_seconds", "q4_seconds",
    "dominant_q", "frequency_rank",
]

BROWSER_EXES = {
    "zen.exe", "chrome.exe", "msedge.exe", "firefox.exe",
    "opera.exe", "brave.exe", "vivaldi.exe",
}

# --- Define base sets first so the loaders below can .update() them ---
IDLE_TITLES: set = {"Desktop", "Task Manager", "Program Manager", "Settings"}
IDLE_EXES:   set = {"explorer.exe", "system"}

# --- Overrides (exe/title → quadrant int) ---
def _load_overrides() -> dict:
    if os.path.isfile(OVERRIDES_JSON_PATH):
        try:
            with open(OVERRIDES_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}

CUSTOM_OVERRIDES: dict = _load_overrides()

# --- Idle exclusions (persisted by correction.py) ---
def _load_idle_exclusions():
    if os.path.isfile(IDLE_EXCLUSIONS_PATH):
        try:
            with open(IDLE_EXCLUSIONS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("idle_exes", [])), set(data.get("idle_titles", []))
        except (json.JSONDecodeError, OSError):
            pass
    return set(), set()

_loaded_exes, _loaded_titles = _load_idle_exclusions()
IDLE_EXES.update(_loaded_exes)
IDLE_TITLES.update(_loaded_titles)