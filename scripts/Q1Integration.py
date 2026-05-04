import pygetwindow as gw
import time
import pandas as pd
import pickle
import re
import requests
from icalendar import Calendar
from datetime import datetime, timezone

BLACKBOARD_URL = "Y" 

def fetch_q1_keywords():
    q1_keywords = set()
    try:
        response = requests.get(BLACKBOARD_URL)
        response.raise_for_status()
        cal = Calendar.from_ical(response.text)
        now = datetime.now(timezone.utc)
        
        for component in cal.walk('vevent'):
            due_date = component.get('dtend').dt
            
            if not isinstance(due_date, datetime):
                due_date = datetime.combine(due_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            
            time_left = (due_date - now).total_seconds() / 3600
            
            if 0 < time_left <= 48:
                raw_title = str(component.get('summary')).lower()
                clean_title = re.sub(r'[^\w\s]', '', raw_title)
                words = [w for w in clean_title.split() if len(w) > 3 and w not in ['quiz', 'exam', 'test', 'assignment']]
                q1_keywords.update(words)
                
        return q1_keywords
    except Exception:
        return set()

ACTIVE_Q1_KEYWORDS = fetch_q1_keywords()

try:
    with open('models/beeware_model_v2.pkl', 'rb') as f:
        core_model = pickle.load(f)
    with open('models/youtube_intent_model.pkl', 'rb') as f:
        intent_model = pickle.load(f)
    with open('models/youtube_vectorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)
except FileNotFoundError:
    exit()

try:
    domains_df = pd.read_csv('data/processed/domain_reference.csv')
    study_domains = set(domains_df[domains_df['label'] == 1]['domain'].dropna().tolist())
    distract_domains = set(domains_df[domains_df['label'] == 0]['domain'].dropna().tolist())
    
    games_df = pd.read_csv('data/raw/steam_games.csv') 
    raw_games = games_df['name'].str.lower().dropna().tolist()
    distract_games = {g for g in raw_games if len(g) > 4 and g not in ['project', 'java', 'code', 'visual', 'task', 'switching', 'youtube', 'browser', 'desktop', 'google']}
    
    ABSOLUTE_DISTRACTIONS = distract_domains.union(distract_games)
    ABSOLUTE_DISTRACTIONS.add('limbuscompany') 
    
    ABSOLUTE_STUDY = study_domains.union({'visual studio code', 'obsidian', 'eclipse', 'intellij', 'pdf', 'canvas', 'instructure', 'blackboard', 'malayanmindanao'})
    
except Exception:
    ABSOLUTE_DISTRACTIONS = {'valorant', 'steam', 'genshin', 'facebook', 'netflix', 'tiktok', 'limbuscompany'}
    ABSOLUTE_STUDY = {'visual studio code', 'notion', 'canvas', 'obsidian', 'github', 'blackboard', 'malayanmindanao'}

def analyze_intent(title):
    clean_title = re.sub(r'^\(\d+\)\s*', '', title)
    clean_title = clean_title.replace(" - YouTube", "").replace(" - Google Chrome", "").replace(" — Zen Browser", "").lower()
    vec = vectorizer.transform([clean_title])
    return "STUDY" if intent_model.predict(vec)[0] == 1 else "DISTRACT"

def get_live_metrics():
    q1_seconds, q2_seconds, q4_seconds, switch_count = 0, 0, 0, 0
    last_window = ""
    
    print("\n" + "="*85)
    print(f"{'Time':<6} | {'Matrix Quadrant':<25} | {'Window Title'}")
    print("="*85)
    
    for i in range(60): 
        try:
            raw_title = gw.getActiveWindowTitle() or "Desktop"
            title_lower = raw_title.lower()
            title_no_spaces = title_lower.replace(" ", "")
            
            if raw_title != last_window:
                switch_count += 1
                last_window = raw_title
            
            category = "OTHER"
            
            if any(d in title_lower for d in ABSOLUTE_DISTRACTIONS) or any(d in title_no_spaces for d in ABSOLUTE_DISTRACTIONS):
                q4_seconds += 1
                category = "Q4: DISTRACT (Rule)"
                
            elif any(s in title_lower for s in ABSOLUTE_STUDY):
                if any(q1_word in title_lower for q1_word in ACTIVE_Q1_KEYWORDS):
                    q1_seconds += 1
                    category = "Q1: URGENT STUDY"
                else:
                    q2_seconds += 1
                    category = "Q2: DEEP WORK"
                    
            elif any(b in title_lower for b in ["youtube", "chrome", "edge", "zen browser"]):
                if analyze_intent(raw_title) == "STUDY":
                    if any(q1_word in title_lower for q1_word in ACTIVE_Q1_KEYWORDS):
                        q1_seconds += 1
                        category = "Q1: URGENT STUDY (AI)"
                    else:
                        q2_seconds += 1
                        category = "Q2: DEEP WORK (AI)"
                else:
                    q4_seconds += 1
                    category = "Q4: DISTRACT (AI)"
                    
            print(f"Sec {i+1:<2} | {category:<25} | {raw_title[:40]}")
        except Exception:
            pass 
        time.sleep(1)
        
    return q1_seconds, q2_seconds, q4_seconds

q1, q2, q4 = get_live_metrics()

print(f"\n--- BEEWARE V4 SESSION RESULTS ---")
print(f"Quadrant 1 (Urgent Fires): {q1} seconds")
print(f"Quadrant 2 (Long-term Growth): {q2} seconds")
print(f"Quadrant 4 (Distractions): {q4} seconds")