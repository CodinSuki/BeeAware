import pygetwindow as gw
import time
import pickle
import win32gui
import win32process
import psutil
import csv
import os
from datetime import datetime

print("--- INITIALIZING BEEWARE UNIVERSAL WATCHER ---")

# --- HELPER FUNCTION: X-RAY VISION ---
def get_active_process_name():
    """Extracts the underlying .exe name of the active window."""
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid)
        return process.name().lower() 
    except Exception:
        return "unknown.exe"

# --- HELPER FUNCTION: PERSISTENT STORAGE ---
def log_session_to_csv(stats, intensity, filename="data/beeware_daily_log.csv"):
    """Appends the session data to a persistent CSV ledger."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    file_exists = os.path.isfile(filename)
    
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['timestamp', 'q1_urgent', 'q2_growth', 'q3_noise', 'q4_play', 'switching_intensity'])
            
        writer.writerow([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            stats[0.0],  # Q1
            stats[1.0],  # Q2
            stats[2.0],  # Q3
            stats[3.0],  # Q4
            intensity
        ])
    print(f">> Session successfully logged to {filename}")

# 1. LOAD THE UNIVERSAL NLP MODEL
try:
    with open('models/eisenhower_model.pkl', 'rb') as f:
        model = pickle.load(f)
    with open('models/tfidf_vectorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)
except FileNotFoundError:
    print("Error: eisenhower_model.pkl or vectorizer not found.")
    exit()

QUADRANTS = {
    0.0: "Q1: URGENT", 
    1.0: "Q2: GROWTH", 
    2.0: "Q3: NOISE", 
    3.0: "Q4: PLAY"
}

CUSTOM_OVERRIDES = {
    "beeware": 1.0,         
    "machinelearning": 1.0, 
    "csv": 1.0,             
    "github": 1.0,          
    "lupadmods": 1.0,
    "blackboard": 0.0,     
    "canvas": 0.0           
}

def get_live_metrics(duration=60):
    stats = {0.0: 0, 1.0: 0, 2.0: 0, 3.0: 0}
    last_window = ""
    switch_count = 0
    
    print("\n" + "="*80)
    print(f"{'Time':<6} | {'Quadrant Classification':<25} | {'Window Title'}")
    print("="*80)
    
    for i in range(duration): 
        try:
            raw_title = gw.getActiveWindowTitle() or "Desktop"
            exe_name = get_active_process_name()
            
            # THE OS BYPASS FILTER
            if raw_title in ["Desktop", "Task Manager", "Program Manager", "Settings"] or exe_name == "explorer.exe":
                print(f"Sec {i+1:<2} | IDLE / SYSTEM             | [{exe_name}] {raw_title[:35]}")
                time.sleep(1)
                continue
            
            # Track switching intensity
            if raw_title != last_window and raw_title != "Desktop":
                switch_count += 1
                last_window = raw_title
            
            # 1.5 USER OVERRIDES
            title_lower = raw_title.lower()
            override_triggered = False
            
            for keyword, force_quadrant in CUSTOM_OVERRIDES.items():
                if keyword in title_lower:
                    prediction = force_quadrant
                    stats[prediction] += 1
                    category = f"{QUADRANTS[prediction]} (Override)"
                    print(f"Sec {i+1:<2} | {category:<25} | [{exe_name}] {raw_title[:35]}")
                    override_triggered = True
                    break
            
            if override_triggered:
                time.sleep(1)
                continue

            # 2. LET THE AI DO THE WORK
            if exe_name in ["zen.exe", "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"]:
                nlp_process = "web browser"
            else:
                nlp_process = exe_name
   
            ai_input = f"{nlp_process} {raw_title}"
            
            vec = vectorizer.transform([ai_input])
            prediction = model.predict(vec)[0]

            stats[prediction] += 1
            category = QUADRANTS[prediction]
                
            print(f"Sec {i+1:<2} | {category:<25} | [{exe_name}] {raw_title[:35]}")
            
        except Exception as e:
            print(f"Sec {i+1:<2} | ERROR                     | {e}")
        time.sleep(1)
        
    return stats, switch_count

# Run the monitor for 60 seconds
session_stats, switches = get_live_metrics(60)

intensity = switches 

print(f"\n--- BEEWARE SESSION VERDICT ---")
print(f"Urgent/Growth Time: {session_stats[0.0] + session_stats[1.0]} seconds")
print(f"Noise/Play Time: {session_stats[2.0] + session_stats[3.0]} seconds")
print(f"Task Switching Intensity: {intensity} switches/min")

if intensity > 10:
    print(">> AI WARNING: High task-switching detected. Group your tasks to maintain focus.")
if session_stats[3.0] > 15: 
    print(">> AI WARNING: Distraction thresholds exceeded. Time to close unnecessary tabs.")

# --- SAVE TO THE DATABASE ---
log_session_to_csv(session_stats, intensity)