import customtkinter as ctk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta
from tkinter import messagebox
import os
import time
import threading
import pickle
import win32gui
import win32process
import psutil
import csv


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

QUADRANTS = {0.0: "Q1: URGENT", 1.0: "Q2: GROWTH", 2.0: "Q3: NOISE", 3.0: "Q4: PLAY"}
CUSTOM_OVERRIDES = {"beeware": 1.0, "machinelearning": 1.0, "csv": 1.0, "github": 1.0, "lupadmods": 1.0, "blackboard": 0.0, "canvas": 0.0}

class BeewareApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Beeware | Live Productivity Engine")
        self.geometry("1200x750")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        
    
        self.is_tracking = False
        self.is_paused = False  
        self.tracking_thread = None
        self.live_stats = {0.0: 0, 1.0: 0, 2.0: 0, 3.0: 0}
        self.switch_count = 0
        self.last_window = ""
        self.last_date_str = "No Data" 
        
        self.current_window = "Waiting..."
        self.current_verdict = "Idle"
        self.current_exe = ""
        

        try:
            with open('models/eisenhower_model.pkl', 'rb') as f:
                self.model = pickle.load(f)
            with open('models/tfidf_vectorizer.pkl', 'rb') as f:
                self.vectorizer = pickle.load(f)
            self.ai_status = "AI Models Loaded."
        except Exception:
            self.ai_status = "ERROR: Models missing!"
            
        self.today_stats, self.yesterday_stats = self.load_data()
        
        self.build_control_panel()
        self.build_summary_panel()
        self.build_graphs_panel()
        
     
        self.protocol("WM_DELETE_WINDOW", self.exit_app)


  
    def load_data(self):
        """Finds Today's stats and the Most Recent available past day."""
        file_path = "data/beeware_daily_log.csv"
        empty_stats = {'q1_urgent': 0, 'q2_growth': 0, 'q3_noise': 0, 'q4_play': 0}
        
        if not os.path.exists(file_path): 
            self.last_date_str = "No History"
            return empty_stats, empty_stats
            
        try:
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            daily = df.groupby('date')[['q1_urgent', 'q2_growth', 'q3_noise', 'q4_play']].sum()
            
            today = datetime.now().date()
            t_data = daily.loc[today].to_dict() if today in daily.index else empty_stats
            
      
            past_dates = [d for d in daily.index if d < today]
            if past_dates:
                latest_past = max(past_dates)
                y_data = daily.loc[latest_past].to_dict()
                self.last_date_str = latest_past.strftime('%b %d')
            else:
                y_data = empty_stats
                self.last_date_str = "No History"
                
            return t_data, y_data
        except Exception as e:
            print(f"Load Error: {e}")
            self.last_date_str = "Error"
            return empty_stats, empty_stats

    def toggle_tracking(self):
        if not self.is_tracking:
            self.is_tracking = True
            self.is_paused = False
            self.btn_toggle.configure(text="End & Save Session", fg_color="#ff6b6b")
            self.btn_pause.configure(state="normal")
            self.lbl_status.configure(text="Status: WATCHING", text_color="#51cf66")
            
            self.tracking_thread = threading.Thread(target=self.watcher_loop, daemon=True)
            self.tracking_thread.start()
            self.update_live_ui()
        else:
            self.exit_app()

    def toggle_pause(self):
        if self.is_tracking:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.btn_pause.configure(text="Resume AI", fg_color="#fcc419")
                self.lbl_status.configure(text="Status: PRIVACY PAUSE", text_color="#fcc419")
            else:
                self.btn_pause.configure(text="Privacy Pause", fg_color="#495057")
                self.lbl_status.configure(text="Status: WATCHING", text_color="#51cf66")

    def exit_app(self):
        """Stops the main loop first to prevent 'invalid command' errors."""
        if self.is_tracking:
            if messagebox.askyesno("Exit Beeware", "Session active! Save and close?"):
                self.is_tracking = False 
                self.save_live_session()
                self.quit() 
        else:
            self.is_tracking = False
            self.quit()

    def save_live_session(self):
        filename = "data/beeware_daily_log.csv"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        file_exists = os.path.isfile(filename)
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['timestamp', 'q1_urgent', 'q2_growth', 'q3_noise', 'q4_play', 'switching_intensity'])
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                self.live_stats[0.0], self.live_stats[1.0], self.live_stats[2.0], self.live_stats[3.0], self.switch_count
            ])

    def watcher_loop(self):
        import pygetwindow as gw 
        while self.is_tracking:
            try:
                raw_title = gw.getActiveWindowTitle() or "Desktop"
                exe_name = self.get_active_process_name()
                self.current_window = raw_title
                self.current_exe = exe_name
                
                if self.is_paused:
                    self.current_verdict = "HIDDEN (Privacy Mode)"
                    time.sleep(1)
                    continue

                if raw_title in ["Desktop", "Task Manager", "Program Manager", "Settings"] or exe_name == "explorer.exe":
                    self.current_verdict = "IDLE / SYSTEM"
                    time.sleep(1)
                    continue
                
                if raw_title != self.last_window:
                    self.switch_count += 1
                    self.last_window = raw_title
                
                override = False
                for kw, q in CUSTOM_OVERRIDES.items():
                    if kw in raw_title.lower():
                        self.live_stats[q] += 1
                        self.current_verdict = f"{QUADRANTS[q]} (Override)"
                        override = True
                        break
                if not override:
                    nlp_process = "web browser" if exe_name in ["zen.exe", "chrome.exe"] else exe_name
                    ai_input = f"{nlp_process} {raw_title}"
                    vec = self.vectorizer.transform([ai_input])
                    pred = self.model.predict(vec)[0]
                    self.live_stats[pred] += 1
                    self.current_verdict = QUADRANTS[pred]

            except Exception as e: print(f"Watcher Error: {e}")
            time.sleep(1)

    def get_active_process_name(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).name().lower()
        except: return "unknown.exe"

    def format_time(self, seconds):
        """Helper to turn raw seconds into a pretty string."""
        mins, secs = divmod(int(seconds), 60)
        return f"{mins}m {secs:02d}s"

    def update_live_ui(self):
        if not self.is_tracking:
            return 

        try:
            if self.winfo_exists():
                
                prod_sec = self.live_stats[0.0] + self.live_stats[1.0]
                dist_sec = self.live_stats[2.0] + self.live_stats[3.0]
                
                self.lbl_live_prod.configure(text=f"Live Focus: {self.format_time(prod_sec)}")
                self.lbl_live_dist.configure(text=f"Live Distracted: {self.format_time(dist_sec)}")
                
                
                if self.is_paused:
                    self.sum_frame.configure(fg_color="#3d3d3d") #
                    self.lbl_ai_verdict.configure(text_color="gray")
                else:
                    self.sum_frame.configure(fg_color="#2b2b2b") 
                    self.lbl_ai_verdict.configure(text_color="#339af0")

                display_title = self.current_window[:35] + "..." if len(self.current_window) > 35 else self.current_window
                self.lbl_active_window.configure(text=f"App: [{self.current_exe}]\nTitle: {display_title}")
                self.lbl_ai_verdict.configure(text=f"AI Verdict: {self.current_verdict}")
                
                self.after(1000, self.update_live_ui)
        except Exception:
            pass

   
    def build_control_panel(self):
        frame = ctk.CTkFrame(self, height=100, corner_radius=10)
        frame.grid(row=0, column=0, columnspan=2, padx=20, pady=(20,0), sticky="ew")
        
        self.btn_toggle = ctk.CTkButton(frame, text="Start Session", height=40, command=self.toggle_tracking)
        self.btn_toggle.pack(side="left", padx=20, pady=20)
        
        self.btn_pause = ctk.CTkButton(frame, text="Privacy Pause", fg_color="#495057", state="disabled", command=self.toggle_pause)
        self.btn_pause.pack(side="left", padx=10)
        
        self.lbl_status = ctk.CTkLabel(frame, text="Status: IDLE", font=ctk.CTkFont(size=16))
        self.lbl_status.pack(side="left", padx=20)
        
        ctk.CTkLabel(frame, text=self.ai_status, font=ctk.CTkFont(size=12), text_color="gray").pack(side="right", padx=20)

    def build_summary_panel(self):
        self.sum_frame = ctk.CTkFrame(self, corner_radius=15)
        self.sum_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        
        ctk.CTkLabel(self.sum_frame, text="Live Monitor", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 10))
        self.lbl_live_prod = ctk.CTkLabel(self.sum_frame, text="Live Focus: 0 sec", text_color="#51cf66")
        self.lbl_live_prod.pack()
        self.lbl_live_dist = ctk.CTkLabel(self.sum_frame, text="Live Distracted: 0 sec", text_color="#ff6b6b")
        self.lbl_live_dist.pack()
        
        ctk.CTkLabel(self.sum_frame, text="──────────────", text_color="gray").pack(pady=10)
        self.lbl_active_window = ctk.CTkLabel(self.sum_frame, text="App: IDLE\nTitle: IDLE", font=ctk.CTkFont(size=12), justify="left")
        self.lbl_active_window.pack(pady=5)
        self.lbl_ai_verdict = ctk.CTkLabel(self.sum_frame, text="AI Verdict: Idle", font=ctk.CTkFont(size=15, weight="bold"), text_color="#339af0")
        self.lbl_ai_verdict.pack(pady=10)

    def build_graphs_panel(self):
        self.graph_frame = ctk.CTkFrame(self, corner_radius=15)
        self.graph_frame.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")
        self.refresh_graphs()

    def refresh_graphs(self):
        for widget in self.graph_frame.winfo_children(): widget.destroy()
            
        plt.style.use('dark_background')
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), dpi=100)
        fig.patch.set_facecolor('#2b2b2b') 
        
        colors = ['#339af0', '#51cf66', '#fcc419', '#ff6b6b']
        labels = ['Q1', 'Q2', 'Q3', 'Q4']

        y_sizes = list(self.yesterday_stats.values())
        if sum(y_sizes) > 0:
            ax1.pie(y_sizes, labels=labels, colors=colors, autopct='%1.0f%%', startangle=140)
            ax1.set_title(f"Latest Session ({self.last_date_str})")
        else:
            ax1.text(0.5, 0.5, "No Historical Data", ha='center')
            ax1.axis('off')

        t_sizes = list(self.today_stats.values())
        if sum(t_sizes) > 0:
            ax2.pie(t_sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
            ax2.set_title("Today's Total")
        else:
            ax2.text(0.5, 0.5, "No Data Today Yet", ha='center')
            ax2.axis('off')

        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

if __name__ == "__main__":
    app = BeewareApp()
    app.mainloop()
 
    try:
        app.destroy()
    except:
        pass