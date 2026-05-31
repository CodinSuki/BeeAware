# config.py — all constants for BeeAware
# Imported by every module. Has zero dependencies of its own.

import os
import sys

# When running as a PyInstaller .exe, sys.frozen is True and paths must be
# resolved relative to the executable, not the script file.
if getattr(sys, 'frozen', False):
    # Running as bundled .exe
    BUNDLE_DIR = sys._MEIPASS                    # read-only bundled assets (models)
    BASE_DIR   = os.path.dirname(sys.executable) # writable folder next to .exe (data)
else:
    # Running as normal .py script
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR   = BUNDLE_DIR

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

# Eisenhower quadrants 
QUADRANTS = {0: "Q1: URGENT", 1: "Q2: GROWTH", 2: "Q3: NOISE", 3: "Q4: PLAY"}
Q_COLORS  = {0: BEE_RED, 1: BEE_GREEN, 2: BEE_AMBER, 3: BEE_GOLD}

# Keyword overrides 
CUSTOM_OVERRIDES = {
    "beeware":         0,
    "machinelearning": 0,
    "csv":             0,
    "github":          0,
    "lupadmods":       0,
    "blackboard":      1,
    "canvas":          1,
}

# File paths
# Data files — writable, stored next to the .exe (or script root during dev)
ERROR_LOG_PATH    = os.path.join(BASE_DIR, "data", "beeware_errors.log")
DAILY_LOG_PATH    = os.path.join(BASE_DIR, "data", "beeware_daily_log.csv")
APP_HISTORY_PATH  = os.path.join(BASE_DIR, "data", "beeware_app_history.csv")

# App history CSV schema 
APP_HISTORY_COLS = [
    "date",           # YYYY-MM-DD
    "session_ts",     # full datetime of session end — ties rows to a session
    "exe_name",       # process name e.g. chrome.exe
    "total_seconds",  # total seconds that exe was foreground this session
    "q1_seconds",
    "q2_seconds",
    "q3_seconds",
    "q4_seconds",
    "dominant_q",     # 0-3, whichever quadrant had the most seconds
    "frequency_rank", # rank within this session (1 = most used)
]

# Models — read-only, loaded from bundle when frozen, script root during dev
MODEL_PATH      = os.path.join(BUNDLE_DIR, "models", "V2eisenhower_model.pkl")
VECTORIZER_PATH = os.path.join(BUNDLE_DIR, "models", "V2tfidf_vectorizer.pkl")

# Browser process names
BROWSER_EXES = {"zen.exe", "chrome.exe"}

# System / idle process names and window titles to skip 
IDLE_TITLES = {"Desktop", "Task Manager", "Program Manager", "Settings"}
IDLE_EXES   = {"explorer.exe", "system"}