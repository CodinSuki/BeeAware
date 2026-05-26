import customtkinter as ctk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
from tkinter import messagebox
import os
import time
import threading
import pickle
import win32gui
import win32process
import psutil
import csv
import pygetwindow as gw


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

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

CUSTOM_OVERRIDES = {
    "beeware":         0,
    "machinelearning": 0,
    "csv":             0,
    "github":          0,
    "lupadmods":       0,
    "blackboard":      1,
    "canvas":          1,
}

# ── FIX 2: Error log path ────────────────────────────────────────────────────
ERROR_LOG_PATH   = "data/beeware_errors.log"

# ── App history DB ────────────────────────────────────────────────────────────
APP_HISTORY_PATH = "data/beeware_app_history.csv"
APP_HISTORY_COLS = [
    "date",           # YYYY-MM-DD  — for daily grouping
    "session_ts",     # full datetime of session end — ties rows to a session
    "exe_name",       # process name e.g. chrome.exe
    "total_seconds",  # total seconds that exe was foreground this session
    "q1_seconds",     # seconds classified as Q1 this session
    "q2_seconds",
    "q3_seconds",
    "q4_seconds",
    "dominant_q",     # 0-3, whichever quadrant had the most seconds
    "frequency_rank", # rank within this session (1 = most used)
]

def log_error(context: str, exc: Exception):
    """Write timestamped errors to a persistent log file instead of just printing."""
    os.makedirs(os.path.dirname(ERROR_LOG_PATH), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{context}] {type(exc).__name__}: {exc}\n"
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass  # last resort: silently ignore if log itself fails
    print(line.strip())   # still print for live debugging


class BeewareApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Beeware | Live Productivity Engine")
        self.geometry("1280x780")
        self.configure(fg_color=BEE_COMB)

        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)  # app freq panel — fixed height
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)

        self.is_tracking     = False
        self.is_paused       = False
        self.graphs_visible  = True
        self.tracking_thread = None
        self.live_stats      = {0: 0, 1: 0, 2: 0, 3: 0}
        self.switch_count    = 0
        self.last_window     = ""
        self.last_date_str   = "No Data"

        # App frequency tracker: { exe_name: {"seconds": int, "quadrant_counts": {0:0,1:0,2:0,3:0}} }
        self.app_freq        = {}

        self.current_window  = "Waiting..."
        self.current_verdict = "Idle"
        self.current_exe     = ""
        self.graph_tick      = 0
        self.chart_view      = "pie"   # "pie" | "bar"

        # ── FIX 1: Model load guard ──────────────────────────────────────────
        self.models_ready = False
        self.model        = None
        self.vectorizer   = None

        try:
            with open('models/V2eisenhower_model.pkl', 'rb') as f:
                self.model = pickle.load(f)
            with open('models/V2tfidf_vectorizer.pkl', 'rb') as f:
                self.vectorizer = pickle.load(f)
            self.models_ready = True
            self.ai_status = "AI Models Loaded"
        except FileNotFoundError as e:
            self.ai_status = "ERROR: Models missing!"
            log_error("model_load", e)
        except Exception as e:
            self.ai_status = "ERROR: Model load failed!"
            log_error("model_load", e)

        self.today_stats, self.yesterday_stats = self.load_data()

        self.build_control_panel()
        self.build_monitor_panel()
        self.build_graphs_panel()
        self.build_app_freq_panel()

        # ── FIX 1: Show blocking modal if models didn't load ─────────────────
        if not self.models_ready:
            self.after(200, self._show_model_error_modal)

        self.protocol("WM_DELETE_WINDOW", self.exit_app)

    def _show_model_error_modal(self):
        """Block session start and clearly explain the missing models problem."""
        messagebox.showerror(
            "Models Not Found — Beeware",
            "AI classification models could not be loaded.\n\n"
            "Expected files:\n"
            "  • models/V2eisenhower_model.pkl\n"
            "  • models/V2tfidf_vectorizer.pkl\n\n"
            "Tracking is disabled until models are present.\n"
            f"Details written to: {ERROR_LOG_PATH}"
        )
        # Keep Start button disabled so user cannot start a broken session
        self.btn_toggle.configure(state="disabled", text="Models Missing", fg_color=BEE_RED)

    def load_data(self):
        file_path   = "data/beeware_daily_log.csv"
        empty_stats = {'q1_urgent': 0, 'q2_growth': 0, 'q3_noise': 0, 'q4_play': 0}

        if not os.path.exists(file_path):
            self.last_date_str = "No History"
            return empty_stats, empty_stats

        try:
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            daily = df.groupby('date')[['q1_urgent', 'q2_growth', 'q3_noise', 'q4_play']].sum()

            today  = datetime.now().date()
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
            log_error("load_data", e)   # FIX 2: log instead of bare print
            self.last_date_str = "Error"
            return empty_stats, empty_stats

    def toggle_tracking(self):
        if not self.is_tracking:
            # ── FIX 1: Guard — do not start if models are missing ────────────
            if not self.models_ready:
                self._show_model_error_modal()
                return

            self.is_tracking = True
            self.is_paused   = False
            self.btn_toggle.configure(text="End & Save Session", fg_color=BEE_RED, hover_color="#8f3f30")
            self.btn_pause.configure(state="normal")
            self.lbl_status.configure(text="WATCHING", text_color=BEE_GREEN)
            self.dot_status.configure(text="●", text_color=BEE_GREEN)

            self.tracking_thread = threading.Thread(target=self.watcher_loop, daemon=True)
            self.tracking_thread.start()
            self.update_live_ui()
        else:
            self.exit_app()

    def toggle_pause(self):
        if self.is_tracking:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.btn_pause.configure(text="Resume", fg_color=BEE_AMBER_DIM)
                self.lbl_status.configure(text="PAUSED", text_color=BEE_GOLD)
                self.dot_status.configure(text="●", text_color=BEE_GOLD)
            else:
                self.btn_pause.configure(text="Privacy Pause", fg_color=BEE_BROWN)
                self.lbl_status.configure(text="WATCHING", text_color=BEE_GREEN)
                self.dot_status.configure(text="●", text_color=BEE_GREEN)

    def toggle_graphs(self):
        self.graphs_visible = not self.graphs_visible
        if self.graphs_visible:
            self.graph_frame.grid()
            self.grid_columnconfigure(1, weight=3)
            self.btn_graphs.configure(text="Hide Charts ")
        else:
            self.graph_frame.grid_remove()
            self.grid_columnconfigure(1, weight=0)
            self.btn_graphs.configure(text="Show Charts ")

    def exit_app(self):
        if self.is_tracking:
            if messagebox.askyesno("Exit Beeware", "Session active! Save and close?"):
                self.is_tracking = False
                self.save_live_session()
                self.quit()
        else:
            self.is_tracking = False
            self.quit()

    def save_live_session(self):
        filename   = "data/beeware_daily_log.csv"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        file_exists = os.path.isfile(filename)
        try:
            with open(filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['timestamp', 'q1_urgent', 'q2_growth', 'q3_noise', 'q4_play', 'switching_intensity'])
                writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    self.live_stats[0], self.live_stats[1], self.live_stats[2], self.live_stats[3],
                    self.switch_count
                ])
        except Exception as e:
            log_error("save_live_session", e)   # FIX 2
        # Always save app history alongside the session log
        self.save_app_history()

    def save_app_history(self):
        """
        Append one row per tracked app to beeware_app_history.csv at session end.
        Each row represents a single app's usage within one session, enabling
        cross-session frequency analysis and context-aware pattern detection.
        """
        if not self.app_freq:
            return  # nothing tracked this session

        os.makedirs(os.path.dirname(APP_HISTORY_PATH), exist_ok=True)
        file_exists = os.path.isfile(APP_HISTORY_PATH)
        session_ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_str    = datetime.now().strftime("%Y-%m-%d")

        # Sort by total seconds descending to assign frequency rank
        ranked = sorted(self.app_freq.items(), key=lambda x: x[1]["seconds"], reverse=True)

        try:
            with open(APP_HISTORY_PATH, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(APP_HISTORY_COLS)
                for rank, (exe_name, data) in enumerate(ranked, start=1):
                    qc          = data["quadrant_counts"]
                    dominant_q  = max(qc, key=qc.get)
                    writer.writerow([
                        date_str,
                        session_ts,
                        exe_name,
                        data["seconds"],
                        qc[0], qc[1], qc[2], qc[3],
                        dominant_q,
                        rank,
                    ])
        except Exception as e:
            log_error("save_app_history", e)

    def watcher_loop(self):
        while self.is_tracking:
            try:
                raw_title = gw.getActiveWindowTitle() or "Desktop"
                exe_name  = self.get_active_process_name()
                self.current_window = raw_title
                self.current_exe    = exe_name

                if self.is_paused:
                    self.current_verdict = "HIDDEN (Privacy Mode)"
                    time.sleep(1)
                    continue

                if raw_title in ["Desktop", "Task Manager", "Program Manager", "Settings"] or exe_name in ["explorer.exe", "system"]:
                    self.current_verdict = "IDLE / SYSTEM"
                    time.sleep(1)
                    continue

                if raw_title != self.last_window:
                    self.switch_count += 1
                    self.last_window = raw_title

                normalized = raw_title.lower().replace(" ", "").replace("-", "")

                override = False
                for kw, q in CUSTOM_OVERRIDES.items():
                    if kw in normalized:
                        self.live_stats[q] += 1
                        self.current_verdict = f"{QUADRANTS[q]} (Override)"
                        override = True
                        break

                if not override:
                    nlp_input = "web browser " + raw_title if exe_name in ["zen.exe", "chrome.exe"] else exe_name + " " + raw_title
                    vec  = self.vectorizer.transform([nlp_input])
                    pred = int(self.model.predict(vec)[0])
                    self.live_stats[pred] += 1
                    self.current_verdict = QUADRANTS[pred]

                # ── App frequency tracker ────────────────────────────────────
                # Determine the quadrant that was just assigned this tick
                active_q = next(
                    (q for q, name in QUADRANTS.items() if name in self.current_verdict), None
                )
                if active_q is not None:
                    if exe_name not in self.app_freq:
                        self.app_freq[exe_name] = {"seconds": 0, "quadrant_counts": {0: 0, 1: 0, 2: 0, 3: 0}}
                    self.app_freq[exe_name]["seconds"] += 1
                    self.app_freq[exe_name]["quadrant_counts"][active_q] += 1

            except Exception as e:
                log_error("watcher_loop", e)    # FIX 2: log to file, not just print

            time.sleep(1)

    def get_app_freq_summary(self, top_n=5):
        """
        Returns sorted app usage data for the current session.
        Each entry: (exe_name, total_seconds, dominant_quadrant)
        Dominant quadrant = whichever quadrant accumulated the most seconds for that app.
        """
        summary = []
        for exe, data in self.app_freq.items():
            dominant_q = max(data["quadrant_counts"], key=data["quadrant_counts"].get)
            summary.append((exe, data["seconds"], dominant_q))
        summary.sort(key=lambda x: x[1], reverse=True)
        most_used  = summary[:top_n]
        least_used = summary[-top_n:] if len(summary) > top_n else []
        least_used = [a for a in least_used if a not in most_used]  # no overlap
        return most_used, least_used

    def get_active_process_name(self):
        """
        FIX 3: Return 'system' for protected processes instead of 'unknown.exe'.
        This prevents protected system processes from being classified by the ML model
        and gives them a clear, intentional label that the watcher_loop can filter out.
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).name().lower()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            # Known failure mode: protected OS processes deny access
            # Label clearly as system rather than unknown so watcher can skip them
            return "system"
        except Exception as e:
            log_error("get_active_process_name", e)   # FIX 2: log unexpected errors
            return "system"

    def format_time(self, seconds):
        mins, secs = divmod(int(seconds), 60)
        return f"{mins}m {secs:02d}s"

    def update_live_ui(self):
        if not self.is_tracking:
            return

        try:
            if self.winfo_exists():
                prod_sec = self.live_stats[0] + self.live_stats[1]
                dist_sec = self.live_stats[2] + self.live_stats[3]

                self.lbl_live_prod.configure(text=self.format_time(prod_sec))
                self.lbl_live_dist.configure(text=self.format_time(dist_sec))

                for q, lbl in self.q_time_labels.items():
                    lbl.configure(text=self.format_time(self.live_stats[q]))

                self.lbl_switches.configure(text=str(self.switch_count))
                self.update_app_freq_panel()

                if self.is_paused:
                    self.monitor_frame.configure(fg_color=BEE_COMB_MID)
                    self.lbl_verdict_val.configure(text_color=BEE_GRAY)
                else:
                    self.monitor_frame.configure(fg_color=BEE_COMB_LIGHT)
                    verdict_q = next((q for q, name in QUADRANTS.items() if name in self.current_verdict), None)
                    self.lbl_verdict_val.configure(text_color=Q_COLORS.get(verdict_q, BEE_GOLD))

                self.lbl_exe_val.configure(text=self.current_exe)
                self.lbl_title_val.configure(text=self.current_window)
                self.lbl_verdict_val.configure(text=self.current_verdict)

                self.graph_tick += 1
                if self.graphs_visible and self.graph_tick % 10 == 0:
                    self.refresh_graphs()

                self.after(1000, self.update_live_ui)
        except Exception as e:
            log_error("update_live_ui", e)   # FIX 2

    def build_control_panel(self):
        frame = ctk.CTkFrame(self, height=70, corner_radius=10, fg_color=BEE_COMB_LIGHT)
        frame.grid(row=0, column=0, columnspan=2, padx=20, pady=(16, 0), sticky="ew")
        frame.grid_propagate(False)
        frame.grid_columnconfigure(3, weight=1)

        self.btn_toggle = ctk.CTkButton(
            frame, text="Start Session", width=150, height=38,
            fg_color=BEE_AMBER, hover_color=BEE_AMBER_DIM, text_color=BEE_COMB,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.toggle_tracking
        )
        self.btn_toggle.grid(row=0, column=0, padx=(16, 8), pady=16)

        self.btn_pause = ctk.CTkButton(
            frame, text="Privacy Pause", width=130, height=38,
            fg_color=BEE_BROWN, hover_color=BEE_COMB_MID, text_color=BEE_CREAM,
            font=ctk.CTkFont(size=13),
            state="disabled", command=self.toggle_pause
        )
        self.btn_pause.grid(row=0, column=1, padx=8, pady=16)

        self.btn_graphs = ctk.CTkButton(
            frame, text="Hide Charts", width=130, height=38,
            fg_color=BEE_COMB_MID, hover_color=BEE_BROWN, text_color=BEE_CREAM,
            font=ctk.CTkFont(size=13),
            command=self.toggle_graphs
        )
        self.btn_graphs.grid(row=0, column=2, padx=8, pady=16)

        status_box = ctk.CTkFrame(frame, fg_color="transparent")
        status_box.grid(row=0, column=3, padx=16, sticky="w")

        self.dot_status = ctk.CTkLabel(
            status_box, text="●", text_color=BEE_GRAY, font=ctk.CTkFont(size=12)
        )
        self.dot_status.pack(side="left", padx=(0, 6))

        self.lbl_status = ctk.CTkLabel(
            status_box, text="IDLE",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=BEE_GRAY
        )
        self.lbl_status.pack(side="left")

        ctk.CTkLabel(
            frame, text=self.ai_status,
            font=ctk.CTkFont(size=11), text_color=BEE_GRAY if self.models_ready else BEE_RED
        ).grid(row=0, column=4, padx=16, sticky="e")

    def build_monitor_panel(self):
        self.monitor_frame = ctk.CTkFrame(self, corner_radius=15, fg_color=BEE_COMB_LIGHT)
        self.monitor_frame.grid(row=1, column=0, padx=(20, 10), pady=16, sticky="nsew")
        self.monitor_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.monitor_frame, text="Live Monitor",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=BEE_GOLD
        ).pack(pady=(20, 4))

        ctk.CTkLabel(
            self.monitor_frame, text="─" * 28,
            text_color=BEE_BROWN, font=ctk.CTkFont(size=10)
        ).pack()

        totals_frame = ctk.CTkFrame(self.monitor_frame, fg_color=BEE_COMB_MID, corner_radius=10)
        totals_frame.pack(fill="x", padx=16, pady=(10, 6))
        totals_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(totals_frame, text="Focus", font=ctk.CTkFont(size=11), text_color=BEE_GRAY).grid(row=0, column=0, pady=(10, 0))
        ctk.CTkLabel(totals_frame, text="Distracted", font=ctk.CTkFont(size=11), text_color=BEE_GRAY).grid(row=0, column=1, pady=(10, 0))

        self.lbl_live_prod = ctk.CTkLabel(
            totals_frame, text="0m 00s",
            font=ctk.CTkFont(size=20, weight="bold"), text_color=BEE_GREEN
        )
        self.lbl_live_prod.grid(row=1, column=0, pady=(0, 10))

        self.lbl_live_dist = ctk.CTkLabel(
            totals_frame, text="0m 00s",
            font=ctk.CTkFont(size=20, weight="bold"), text_color=BEE_RED
        )
        self.lbl_live_dist.grid(row=1, column=1, pady=(0, 10))

        q_frame = ctk.CTkFrame(self.monitor_frame, fg_color=BEE_COMB_MID, corner_radius=10)
        q_frame.pack(fill="x", padx=16, pady=6)
        q_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.q_time_labels = {}
        for i, (q, name) in enumerate(QUADRANTS.items()):
            short = name.split(":")[0]
            ctk.CTkLabel(
                q_frame, text=short, font=ctk.CTkFont(size=10), text_color=BEE_GRAY
            ).grid(row=0, column=i, pady=(8, 0), padx=4)
            lbl = ctk.CTkLabel(
                q_frame, text="0m 00s",
                font=ctk.CTkFont(size=12, weight="bold"), text_color=Q_COLORS[q]
            )
            lbl.grid(row=1, column=i, pady=(0, 8), padx=4)
            self.q_time_labels[q] = lbl

        ctk.CTkLabel(
            self.monitor_frame, text="─" * 28,
            text_color=BEE_BROWN, font=ctk.CTkFont(size=10)
        ).pack(pady=(8, 4))

        active_frame = ctk.CTkFrame(self.monitor_frame, fg_color=BEE_COMB_MID, corner_radius=10)
        active_frame.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(
            active_frame, text="PROCESS",
            font=ctk.CTkFont(size=10), text_color=BEE_GRAY
        ).pack(anchor="w", padx=12, pady=(10, 0))

        self.lbl_exe_val = ctk.CTkLabel(
            active_frame, text="—",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=BEE_CREAM,
            wraplength=300, justify="left"
        )
        self.lbl_exe_val.pack(anchor="w", padx=12, pady=(2, 8))

        ctk.CTkLabel(
            active_frame, text="WINDOW TITLE",
            font=ctk.CTkFont(size=10), text_color=BEE_GRAY
        ).pack(anchor="w", padx=12)

        self.lbl_title_val = ctk.CTkLabel(
            active_frame, text="—",
            font=ctk.CTkFont(size=12), text_color=BEE_CREAM,
            wraplength=300, justify="left"
        )
        self.lbl_title_val.pack(anchor="w", padx=12, pady=(2, 12))

        verdict_frame = ctk.CTkFrame(self.monitor_frame, fg_color=BEE_COMB_MID, corner_radius=10)
        verdict_frame.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(
            verdict_frame, text="AI VERDICT",
            font=ctk.CTkFont(size=10), text_color=BEE_GRAY
        ).pack(pady=(10, 2))

        self.lbl_verdict_val = ctk.CTkLabel(
            verdict_frame, text="Idle",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=BEE_GOLD
        )
        self.lbl_verdict_val.pack(pady=(0, 10))

        switches_frame = ctk.CTkFrame(self.monitor_frame, fg_color="transparent")
        switches_frame.pack(fill="x", padx=16, pady=(8, 16))

        ctk.CTkLabel(
            switches_frame, text="Window switches:",
            font=ctk.CTkFont(size=11), text_color=BEE_GRAY
        ).pack(side="left")

        self.lbl_switches = ctk.CTkLabel(
            switches_frame, text="0",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=BEE_CREAM
        )
        self.lbl_switches.pack(side="left", padx=6)

    def build_app_freq_panel(self):
        """
        Fixed-height panel at the bottom of the left column (row 2).
        Shows Most Used (top 3) and Least Used (bottom 3) apps for the current
        session, each with their total time and dominant Q badge.
        Populated by update_app_freq_panel() on every UI tick.
        """
        self.freq_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=BEE_COMB_LIGHT)
        self.freq_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 14), sticky="ew")
        self.freq_frame.grid_columnconfigure(0, weight=1)
        self.freq_frame.grid_columnconfigure(1, weight=1)

        # ── Header ────────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self.freq_frame, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 4))

        ctk.CTkLabel(
            header, text="App Frequency",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=BEE_GOLD
        ).pack(side="left")

        self.lbl_freq_source = ctk.CTkLabel(
            header, text="— no session yet —",
            font=ctk.CTkFont(size=10), text_color=BEE_GRAY
        )
        self.lbl_freq_source.pack(side="left", padx=10)

        # ── Most Used column ──────────────────────────────────────────────────
        most_col = ctk.CTkFrame(self.freq_frame, fg_color=BEE_COMB_MID, corner_radius=8)
        most_col.grid(row=1, column=0, padx=(12, 6), pady=(0, 10), sticky="nsew")
        most_col.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            most_col, text="▲  Most Used",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=BEE_GREEN
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 4))

        self.most_used_rows = []
        for i in range(3):
            row_frame = ctk.CTkFrame(most_col, fg_color="transparent")
            row_frame.grid(row=i + 1, column=0, sticky="ew", padx=8, pady=2)
            row_frame.grid_columnconfigure(1, weight=1)

            badge = ctk.CTkLabel(row_frame, text="Q?", width=36, height=20,
                                 fg_color=BEE_GRAY, corner_radius=4,
                                 font=ctk.CTkFont(size=9, weight="bold"), text_color=BEE_COMB)
            badge.grid(row=0, column=0, padx=(0, 6))

            name_lbl = ctk.CTkLabel(row_frame, text="—",
                                    font=ctk.CTkFont(size=11), text_color=BEE_CREAM,
                                    anchor="w")
            name_lbl.grid(row=0, column=1, sticky="w")

            time_lbl = ctk.CTkLabel(row_frame, text="",
                                    font=ctk.CTkFont(size=10), text_color=BEE_GRAY,
                                    anchor="e")
            time_lbl.grid(row=0, column=2, sticky="e", padx=(6, 0))

            self.most_used_rows.append((badge, name_lbl, time_lbl))

        # spacer so column has consistent height even with <3 apps
        ctk.CTkLabel(most_col, text="", height=6).grid(row=4, column=0)

        # ── Least Used column ─────────────────────────────────────────────────
        least_col = ctk.CTkFrame(self.freq_frame, fg_color=BEE_COMB_MID, corner_radius=8)
        least_col.grid(row=1, column=1, padx=(6, 12), pady=(0, 10), sticky="nsew")
        least_col.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            least_col, text="▼  Least Used",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=BEE_RED
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 4))

        self.least_used_rows = []
        for i in range(3):
            row_frame = ctk.CTkFrame(least_col, fg_color="transparent")
            row_frame.grid(row=i + 1, column=0, sticky="ew", padx=8, pady=2)
            row_frame.grid_columnconfigure(1, weight=1)

            badge = ctk.CTkLabel(row_frame, text="Q?", width=36, height=20,
                                 fg_color=BEE_GRAY, corner_radius=4,
                                 font=ctk.CTkFont(size=9, weight="bold"), text_color=BEE_COMB)
            badge.grid(row=0, column=0, padx=(0, 6))

            name_lbl = ctk.CTkLabel(row_frame, text="—",
                                    font=ctk.CTkFont(size=11), text_color=BEE_CREAM,
                                    anchor="w")
            name_lbl.grid(row=0, column=1, sticky="w")

            time_lbl = ctk.CTkLabel(row_frame, text="",
                                    font=ctk.CTkFont(size=10), text_color=BEE_GRAY,
                                    anchor="e")
            time_lbl.grid(row=0, column=2, sticky="e", padx=(6, 0))

            self.least_used_rows.append((badge, name_lbl, time_lbl))

        ctk.CTkLabel(least_col, text="", height=6).grid(row=4, column=0)

    def update_app_freq_panel(self):
        """
        Refreshes the most/least used rows from get_app_freq_summary().
        Called every second from update_live_ui during an active session.
        Falls back to APP_HISTORY_PATH for the last saved session when idle.
        Blanks out unused slots cleanly so stale data never shows.
        """
        # ── Decide data source ────────────────────────────────────────────────
        if self.is_tracking and self.app_freq:
            most, least = self.get_app_freq_summary(top_n=3)
            self.lbl_freq_source.configure(text="live session", text_color=BEE_GREEN)
        elif os.path.exists(APP_HISTORY_PATH):
            try:
                df = pd.read_csv(APP_HISTORY_PATH)
                if not df.empty:
                    latest_ts = df["session_ts"].max()
                    df = df[df["session_ts"] == latest_ts].copy()
                    df["total_seconds"] = df[["q1_seconds","q2_seconds","q3_seconds","q4_seconds"]].sum(axis=1)
                    df_sorted = df.sort_values("total_seconds", ascending=False)
                    def _to_tuple(row):
                        return (row["exe_name"], int(row["total_seconds"]), int(row["dominant_q"]))
                    all_apps = [_to_tuple(r) for _, r in df_sorted.iterrows()]
                    most  = all_apps[:3]
                    least = all_apps[-3:][::-1] if len(all_apps) > 3 else []
                    date_label = latest_ts[:10]
                    self.lbl_freq_source.configure(
                        text=f"last session  ({date_label})", text_color=BEE_GRAY
                    )
                else:
                    most, least = [], []
                    self.lbl_freq_source.configure(text="no history yet", text_color=BEE_GRAY)
            except Exception as e:
                log_error("update_app_freq_panel", e)
                most, least = [], []
        else:
            most, least = [], []
            self.lbl_freq_source.configure(text="— no session yet —", text_color=BEE_GRAY)

        # ── Q badge colours ───────────────────────────────────────────────────
        q_badge_colors = {0: BEE_RED, 1: BEE_GREEN, 2: BEE_AMBER, 3: BEE_GOLD}
        q_labels       = {0: "Q1", 1: "Q2", 2: "Q3", 3: "Q4"}

        def _fill_rows(rows_widgets, data):
            for i, (badge, name_lbl, time_lbl) in enumerate(rows_widgets):
                if i < len(data):
                    exe, secs, dominant_q = data[i]
                    mins, s = divmod(secs, 60)
                    time_str = f"{mins}m {s:02d}s" if mins > 0 else f"{s}s"
                    short_name = exe.replace(".exe", "")[:18]  # truncate long names
                    badge.configure(
                        text=q_labels.get(dominant_q, "Q?"),
                        fg_color=q_badge_colors.get(dominant_q, BEE_GRAY)
                    )
                    name_lbl.configure(text=short_name)
                    time_lbl.configure(text=time_str)
                else:
                    # blank out unused slots
                    badge.configure(text="Q?", fg_color=BEE_GRAY)
                    name_lbl.configure(text="—")
                    time_lbl.configure(text="")

        _fill_rows(self.most_used_rows, most)
        _fill_rows(self.least_used_rows, least)

    def build_graphs_panel(self):
        self.graph_frame = ctk.CTkFrame(self, corner_radius=15, fg_color=BEE_COMB_LIGHT)
        self.graph_frame.grid(row=1, column=1, padx=(10, 20), pady=16, sticky="nsew")
        self.graph_frame.grid_rowconfigure(1, weight=1)
        self.graph_frame.grid_columnconfigure(0, weight=1)

        # ── Toggle button row ─────────────────────────────────────────────────
        toggle_row = ctk.CTkFrame(self.graph_frame, fg_color="transparent")
        toggle_row.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 0))

        self.btn_view_pie = ctk.CTkButton(
            toggle_row, text="Pie Charts", width=120, height=28,
            fg_color=BEE_AMBER, hover_color=BEE_AMBER_DIM, text_color=BEE_COMB,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self._switch_chart_view("pie")
        )
        self.btn_view_pie.pack(side="left", padx=(0, 6))

        self.btn_view_bar = ctk.CTkButton(
            toggle_row, text="App Bar Chart", width=130, height=28,
            fg_color=BEE_COMB_MID, hover_color=BEE_BROWN, text_color=BEE_CREAM,
            font=ctk.CTkFont(size=12),
            command=lambda: self._switch_chart_view("bar")
        )
        self.btn_view_bar.pack(side="left")

        # ── Canvas container ──────────────────────────────────────────────────
        self.chart_canvas_frame = ctk.CTkFrame(self.graph_frame, fg_color="transparent")
        self.chart_canvas_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        self.refresh_graphs()

    def _switch_chart_view(self, view: str):
        """Toggle between pie and bar views, updating button states."""
        self.chart_view = view
        if view == "pie":
            self.btn_view_pie.configure(fg_color=BEE_AMBER, text_color=BEE_COMB,
                                        font=ctk.CTkFont(size=12, weight="bold"))
            self.btn_view_bar.configure(fg_color=BEE_COMB_MID, text_color=BEE_CREAM,
                                        font=ctk.CTkFont(size=12))
        else:
            self.btn_view_bar.configure(fg_color=BEE_AMBER, text_color=BEE_COMB,
                                        font=ctk.CTkFont(size=12, weight="bold"))
            self.btn_view_pie.configure(fg_color=BEE_COMB_MID, text_color=BEE_CREAM,
                                        font=ctk.CTkFont(size=12))
        self.refresh_graphs()

    def refresh_graphs(self):
        """Dispatcher — clears canvas frame and draws whichever view is active."""
        for widget in self.chart_canvas_frame.winfo_children():
            widget.destroy()
        if self.chart_view == "pie":
            self._draw_pie_view()
        else:
            self._draw_bar_view()

    def _draw_pie_view(self):
        """Original dual-pie layout: last session vs today."""
        plt.style.use("dark_background")
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4), dpi=100)
        fig.patch.set_facecolor(BEE_COMB_LIGHT)
        ax1.set_facecolor(BEE_COMB_LIGHT)
        ax2.set_facecolor(BEE_COMB_LIGHT)

        colors     = [BEE_RED, BEE_GREEN, BEE_AMBER, BEE_GOLD]
        labels     = ["Q1", "Q2", "Q3", "Q4"]
        text_props = {"color": BEE_CREAM, "fontsize": 9}

        y_sizes = list(self.yesterday_stats.values())
        if sum(y_sizes) > 0:
            _, _, autotexts = ax1.pie(
                y_sizes, labels=labels, colors=colors,
                autopct="%1.0f%%", startangle=140, textprops=text_props
            )
            for at in autotexts:
                at.set_color(BEE_COMB)
                at.set_fontsize(8)
            ax1.set_title(f"Latest Session ({self.last_date_str})", color=BEE_CREAM, pad=12)
        else:
            ax1.text(0.5, 0.5, "No Historical Data", ha="center", va="center", color=BEE_GRAY)
            ax1.axis("off")

        t_sizes = [self.live_stats[q] for q in range(4)] if self.is_tracking else list(self.today_stats.values())
        if sum(t_sizes) > 0:
            _, _, autotexts = ax2.pie(
                t_sizes, labels=labels, colors=colors,
                autopct="%1.1f%%", startangle=140, textprops=text_props
            )
            for at in autotexts:
                at.set_color(BEE_COMB)
                at.set_fontsize(8)
            ax2.set_title("Today's Total", color=BEE_CREAM, pad=12)
        else:
            ax2.text(0.5, 0.5, "No Data Today Yet", ha="center", va="center", color=BEE_GRAY)
            ax2.axis("off")

        fig.tight_layout(pad=2.0)
        canvas = FigureCanvasTkAgg(fig, master=self.chart_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        plt.close(fig)

    def _draw_bar_view(self):
        """
        Horizontal stacked bar chart — one bar per app, segments coloured by Q.
        Data source priority:
          1. self.app_freq  — live session data if tracking is active
          2. APP_HISTORY_PATH — most recent session rows from the CSV if idle
        Top 10 apps by total seconds, sorted descending (most used at top).
        """
        # ── Gather data ───────────────────────────────────────────────────────
        app_data = {}   # exe_name -> {q0..q3 seconds}

        if self.is_tracking and self.app_freq:
            # Live session — use in-memory tracker directly
            for exe, data in self.app_freq.items():
                app_data[exe] = dict(data["quadrant_counts"])
        else:
            # Idle — load most recent session from history CSV
            if os.path.exists(APP_HISTORY_PATH):
                try:
                    df = pd.read_csv(APP_HISTORY_PATH)
                    if not df.empty:
                        latest_ts = df["session_ts"].max()
                        df = df[df["session_ts"] == latest_ts]
                        for _, row in df.iterrows():
                            app_data[row["exe_name"]] = {
                                0: row["q1_seconds"],
                                1: row["q2_seconds"],
                                2: row["q3_seconds"],
                                3: row["q4_seconds"],
                            }
                except Exception as e:
                    log_error("_draw_bar_view", e)

        # ── Nothing to show ───────────────────────────────────────────────────
        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(9, 4), dpi=100)
        fig.patch.set_facecolor(BEE_COMB_LIGHT)
        ax.set_facecolor(BEE_COMB_LIGHT)

        if not app_data:
            ax.text(0.5, 0.5, "No app data yet — start a session",
                    ha="center", va="center", color=BEE_GRAY, fontsize=11)
            ax.axis("off")
            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=self.chart_canvas_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
            plt.close(fig)
            return

        # ── Sort and trim to top 10 ───────────────────────────────────────────
        sorted_apps = sorted(
            app_data.items(),
            key=lambda x: sum(x[1].values()),
            reverse=True
        )[:10]

        # Reverse so most-used renders at the top of the horizontal chart
        sorted_apps = list(reversed(sorted_apps))

        exe_labels  = [a[0].replace(".exe", "") for a in sorted_apps]
        q_seconds   = [[a[1].get(q, 0) for a in sorted_apps] for q in range(4)]
        q_colors    = [BEE_RED, BEE_GREEN, BEE_AMBER, BEE_GOLD]
        q_names     = ["Q1: Urgent", "Q2: Growth", "Q3: Noise", "Q4: Play"]

        # ── Draw stacked horizontal bars ──────────────────────────────────────
        y_pos  = range(len(exe_labels))
        lefts  = [0] * len(exe_labels)

        for q in range(4):
            vals = q_seconds[q]
            bars = ax.barh(
                y_pos, vals, left=lefts,
                color=q_colors[q], label=q_names[q],
                height=0.6, alpha=0.92
            )
            # Inline second labels — only if bar is wide enough to fit text
            for bar, val in zip(bars, vals):
                if val > 30:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_y() + bar.get_height() / 2,
                        f"{val//60}m" if val >= 60 else f"{val}s",
                        ha="center", va="center",
                        fontsize=7, color=BEE_COMB, fontweight="bold"
                    )
            lefts = [l + v for l, v in zip(lefts, vals)]

        # ── Total time label at end of each bar ───────────────────────────────
        for i, (_, qdata) in enumerate(sorted_apps):
            total = sum(qdata.values())
            mins, secs = divmod(total, 60)
            label = f" {mins}m {secs:02d}s" if mins > 0 else f" {secs}s"
            ax.text(lefts[i] + 1, i, label,
                    va="center", fontsize=8, color=BEE_CREAM)

        # ── Axes styling ──────────────────────────────────────────────────────
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(exe_labels, color=BEE_CREAM, fontsize=9)
        ax.xaxis.set_visible(False)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_color(BEE_BROWN)
        ax.tick_params(axis="y", colors=BEE_CREAM, length=0)

        title = "App Usage — Live Session" if self.is_tracking else "App Usage — Last Session"
        ax.set_title(title, color=BEE_CREAM, pad=10, fontsize=11)

        legend = ax.legend(
            loc="lower right", fontsize=8,
            facecolor=BEE_COMB_MID, edgecolor=BEE_BROWN,
            labelcolor=BEE_CREAM, framealpha=0.9
        )

        fig.tight_layout(pad=1.5)
        canvas = FigureCanvasTkAgg(fig, master=self.chart_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=6)
        plt.close(fig)


if __name__ == "__main__":
    app = BeewareApp()
    app.mainloop()
    try:
        app.destroy()
    except Exception:
        pass