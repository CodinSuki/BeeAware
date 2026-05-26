# app.py — BeewareApp core class
# Composes all UI mixins and owns all tracking/data logic.

import os
import csv
import time
import pickle
import threading
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk
import pandas as pd
import win32gui
import win32process
import psutil
import pygetwindow as gw

from config import (
    BEE_COMB, BEE_COMB_LIGHT, BEE_GREEN, BEE_GOLD, BEE_RED,
    BEE_AMBER, BEE_AMBER_DIM, BEE_BROWN, BEE_CREAM,
    QUADRANTS, Q_COLORS, CUSTOM_OVERRIDES,
    ERROR_LOG_PATH, DAILY_LOG_PATH, APP_HISTORY_PATH, APP_HISTORY_COLS,
    MODEL_PATH, VECTORIZER_PATH, BROWSER_EXES, IDLE_TITLES, IDLE_EXES,
)
from logger import log_error
from ui.control_panel import ControlPanelMixin
from ui.monitor_panel  import MonitorPanelMixin
from ui.graphs_panel   import GraphsPanelMixin
from ui.freq_panel     import FreqPanelMixin
from ui.correction     import CorrectionMixin


class BeewareApp(
    ControlPanelMixin,
    MonitorPanelMixin,
    GraphsPanelMixin,
    FreqPanelMixin,
    CorrectionMixin,
    ctk.CTk,
):
    def __init__(self):
        super().__init__()

        self.title("Beeware | Live Productivity Engine")
        self.geometry("1280x780")
        self.configure(fg_color=BEE_COMB)

        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0) 
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)

        #Session state
        self.is_tracking     = False
        self.is_paused       = False
        self.graphs_visible  = True
        self.tracking_thread = None
        self.live_stats      = {0: 0, 1: 0, 2: 0, 3: 0}
        self.switch_count    = 0
        self.last_window     = ""
        self.last_date_str   = "No Data"
        self.chart_view      = "pie"   # "pie" | "bar"

        # App frequency tracker: { exe_name: {"seconds": int, "quadrant_counts": {0:0,...}} }
        self.app_freq        = {}

        # Live monitor state (written by watcher thread, read by UI thread)
        self.current_window  = "Waiting..."
        self.current_verdict = "Idle"
        self.current_exe     = ""
        self.graph_tick      = 0

        # Model load 
        self.models_ready = False
        self.model        = None
        self.vectorizer   = None

        try:
            with open(MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)
            with open(VECTORIZER_PATH, "rb") as f:
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

        # Build UI panels 
        self.build_control_panel()
        self.build_monitor_panel()
        self.build_graphs_panel()
        self.build_app_freq_panel()

        if not self.models_ready:
            self.after(200, self._show_model_error_modal)

        self.protocol("WM_DELETE_WINDOW", self.exit_app)

    # Model error modal 
    def _show_model_error_modal(self):
        messagebox.showerror(
            "Models Not Found — Beeware",
            "AI classification models could not be loaded.\n\n"
            "Expected files:\n"
            f"  • {MODEL_PATH}\n"
            f"  • {VECTORIZER_PATH}\n\n"
            "Tracking is disabled until models are present.\n"
            f"Details written to: {ERROR_LOG_PATH}",
        )
        self.btn_toggle.configure(state="disabled", text="Models Missing", fg_color=BEE_RED)

    # Data loading 
    def load_data(self):
        empty_stats = {"q1_urgent": 0, "q2_growth": 0, "q3_noise": 0, "q4_play": 0}

        if not os.path.exists(DAILY_LOG_PATH):
            self.last_date_str = "No History"
            return empty_stats, empty_stats

        try:
            df    = pd.read_csv(DAILY_LOG_PATH)
            df["date"] = pd.to_datetime(df["timestamp"]).dt.date
            daily = df.groupby("date")[["q1_urgent", "q2_growth", "q3_noise", "q4_play"]].sum()

            today  = datetime.now().date()
            t_data = daily.loc[today].to_dict() if today in daily.index else empty_stats

            past_dates = [d for d in daily.index if d < today]
            if past_dates:
                latest_past = max(past_dates)
                y_data = daily.loc[latest_past].to_dict()
                self.last_date_str = latest_past.strftime("%b %d")
            else:
                y_data = empty_stats
                self.last_date_str = "No History"

            return t_data, y_data
        except Exception as e:
            log_error("load_data", e)
            self.last_date_str = "Error"
            return empty_stats, empty_stats

    #Session control
    def toggle_tracking(self):
        if not self.is_tracking:
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
            self.btn_graphs.configure(text="Hide Charts")
        else:
            self.graph_frame.grid_remove()
            self.grid_columnconfigure(1, weight=0)
            self.btn_graphs.configure(text="Show Charts")

    def exit_app(self):
        if self.is_tracking:
            if messagebox.askyesno("Exit Beeware", "Session active! Save and close?"):
                self.is_tracking = False
                self.save_live_session()
                self.quit()
        else:
            self.is_tracking = False
            self.quit()

    # Data persistence 
    def save_live_session(self):
        os.makedirs(os.path.dirname(DAILY_LOG_PATH), exist_ok=True)
        file_exists = os.path.isfile(DAILY_LOG_PATH)
        try:
            with open(DAILY_LOG_PATH, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["timestamp", "q1_urgent", "q2_growth",
                                     "q3_noise", "q4_play", "switching_intensity"])
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    self.live_stats[0], self.live_stats[1],
                    self.live_stats[2], self.live_stats[3],
                    self.switch_count,
                ])
        except Exception as e:
            log_error("save_live_session", e)
        self.save_app_history()

    def save_app_history(self):
        """Append one row per app to APP_HISTORY_PATH at session end."""
        if not self.app_freq:
            return

        os.makedirs(os.path.dirname(APP_HISTORY_PATH), exist_ok=True)
        file_exists = os.path.isfile(APP_HISTORY_PATH)
        session_ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_str    = datetime.now().strftime("%Y-%m-%d")
        ranked      = sorted(self.app_freq.items(), key=lambda x: x[1]["seconds"], reverse=True)

        try:
            with open(APP_HISTORY_PATH, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(APP_HISTORY_COLS)
                for rank, (exe_name, data) in enumerate(ranked, start=1):
                    qc         = data["quadrant_counts"]
                    dominant_q = max(qc, key=qc.get)
                    writer.writerow([
                        date_str, session_ts, exe_name, data["seconds"],
                        qc[0], qc[1], qc[2], qc[3], dominant_q, rank,
                    ])
        except Exception as e:
            log_error("save_app_history", e)

    #Watcher thread
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

                if raw_title in IDLE_TITLES or exe_name in IDLE_EXES:
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
                    prefix    = "web browser " if exe_name in BROWSER_EXES else exe_name + " "
                    nlp_input = prefix + raw_title
                    vec  = self.vectorizer.transform([nlp_input])
                    pred = int(self.model.predict(vec)[0])
                    self.live_stats[pred] += 1
                    self.current_verdict = QUADRANTS[pred]

                #App frequency tracker
                active_q = next(
                    (q for q, name in QUADRANTS.items() if name in self.current_verdict), None
                )
                if active_q is not None:
                    if exe_name not in self.app_freq:
                        self.app_freq[exe_name] = {"seconds": 0, "quadrant_counts": {0: 0, 1: 0, 2: 0, 3: 0}}
                    self.app_freq[exe_name]["seconds"] += 1
                    self.app_freq[exe_name]["quadrant_counts"][active_q] += 1

            except Exception as e:
                log_error("watcher_loop", e)

            time.sleep(1)

    # Helpers
    def get_active_process_name(self) -> str:
        """Return exe name; 'system' for protected/missing processes (FIX 3)."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).name().lower()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return "system"
        except Exception as e:
            log_error("get_active_process_name", e)
            return "system"

    def get_app_freq_summary(self, top_n: int = 5):
        """
        Return (most_used, least_used) lists, each entry: (exe, seconds, dominant_q).
        Dominant quadrant = the Q with the most seconds for that app this session.
        """
        summary = [
            (exe, data["seconds"], max(data["quadrant_counts"], key=data["quadrant_counts"].get))
            for exe, data in self.app_freq.items()
        ]
        summary.sort(key=lambda x: x[1], reverse=True)
        most  = summary[:top_n]
        least = [a for a in summary[-top_n:] if a not in most]
        return most, least

    def format_time(self, seconds: int) -> str:
        mins, secs = divmod(int(seconds), 60)
        return f"{mins}m {secs:02d}s"
