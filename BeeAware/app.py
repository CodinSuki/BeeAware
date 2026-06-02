# app.py — BeeAwareApp core class
# Composes all UI mixins and owns all tracking/data logic.

import os
import csv
import time
import pickle
import threading
import pystray
from PIL import Image, ImageDraw
import customtkinter as ctk
import pandas as pd
import win32gui
import win32process
import psutil
import pygetwindow as gw

from datetime import datetime
from tkinter import messagebox      
from notif import show_notification
from ui.options import OptionsWindow
from ui.history import HistoryWindow
from ui.summary import SessionSummaryWindow
from ui.floating_bar import FloatingBar

from config import (
    BEE_COMB, BEE_COMB_LIGHT, BEE_GREEN, BEE_GOLD, BEE_RED,
    BEE_AMBER, BEE_AMBER_DIM, BEE_BROWN, BEE_CREAM, BEE_GRAY,
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


def get_active_process_name() -> str:
    """Return exe name for the active foreground window.
    Falls back to 'system' on protected processes or lookup errors.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return psutil.Process(pid).name().lower()
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        return "system"
    except Exception as e:
        log_error("get_active_process_name", e)
        return "system"


class BeeAwareApp(
    ControlPanelMixin,
    MonitorPanelMixin,
    GraphsPanelMixin,
    FreqPanelMixin,
    CorrectionMixin,
    ctk.CTk,
):
    def __init__(self):
        super().__init__()

        self.title("BeeAware | Live Productivity Engine")
        self.geometry("1280x780")
        self.configure(fg_color=BEE_COMB)

        self.grid_rowconfigure(1, weight=3) 
        self.grid_rowconfigure(2, weight=1) 
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.minsize(900, 600) 

        #Session state
        self.is_tracking     = False
        self.is_paused       = False
        self.graphs_visible  = True
        self.tracking_thread = None
        self.session_start   = None  # Track session start time for midnight boundary
        self.live_stats      = {0: 0, 1: 0, 2: 0, 3: 0}
        self.switch_count    = 0
        self.last_window     = None
        self.last_date_str   = "No Data"
        self.chart_view      = "pie"
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

        # Notification state    
        self.notif_cooldown = 0
        self.WARNING_THRESHOLD = 1800 
        self.notifications_enabled = True
        self.silent_tracking = False  # Silent mode: track but no notifications
        self.floating_bar_enabled = True
        self.options_window = None
        self.history_window = None        

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
        self.build_freq_panel()
        self.floating_bar = None 

        if not self.models_ready:
            self.after(200, self._show_model_error_modal)

        # Keyboard shortcuts
        self.bind("<Control-Shift-P>", lambda e: self.toggle_pause())
        self.bind("<Control-Shift-E>", lambda e: self.exit_app())
        self.bind("<Control-Shift-S>", lambda e: self.toggle_silent_tracking())
        self.protocol("WM_DELETE_WINDOW", self._on_close_request)

        # System tray state
        self.tray_icon = None
        self._tray_thread = None
        self._tray_active = False

    def _destroy_floating_bar(self):
        if getattr(self, "floating_bar", None) and self.floating_bar.winfo_exists():
            try:
                self.floating_bar.destroy()
            except Exception:
                pass
            self.floating_bar = None

    def set_floating_bar_visibility(self, enabled: bool):
        self.floating_bar_enabled = enabled
        if getattr(self, "floating_bar", None) and self.floating_bar.winfo_exists():
            try:
                if enabled:
                    self.floating_bar.deiconify()
                    if self.is_tracking:
                        self.floating_bar._expand()
                else:
                    self.floating_bar.withdraw()
            except Exception as e:
                log_error("set_floating_bar_visibility", e)

    # Model error modal 
    def _show_model_error_modal(self):
        messagebox.showerror(
            "Models Not Found — BeeAware",
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
            df = pd.read_csv(DAILY_LOG_PATH)
            
            # Validate columns exist and data is well-formed
            required_cols = ["timestamp", "q1_urgent", "q2_growth", "q3_noise", "q4_play"]
            if not all(col in df.columns for col in required_cols):
                log_error("load_data", "CSV missing required columns")
                self.last_date_str = "Error"
                return empty_stats, empty_stats
            
            # Remove rows with invalid data, skip corrupted entries
            try:
                df["date"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.date
                df = df.dropna(subset=["date"])
                
                # Convert quad columns to numeric, coerce errors to NaN, then drop those rows
                for col in ["q1_urgent", "q2_growth", "q3_noise", "q4_play"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df = df.dropna(subset=["q1_urgent", "q2_growth", "q3_noise", "q4_play"])
                
            except Exception as e:
                log_error("load_data_validation", e)
                self.last_date_str = "Error"
                return empty_stats, empty_stats
            
            if df.empty:
                self.last_date_str = "No History"
                return empty_stats, empty_stats
            
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
            self.session_start = datetime.now()  # Record session start for midnight boundary
            self.btn_toggle.configure(text="End & Save Session", fg_color=BEE_RED, hover_color="#8f3f30")
            self.btn_pause.configure(state="normal")
            self.lbl_status.configure(text="WATCHING", text_color=BEE_GREEN)
            self.dot_status.configure(text="●", text_color=BEE_GREEN)

            self.tracking_thread = threading.Thread(target=self.watcher_loop, daemon=True)
            self.tracking_thread.start()
            if self.floating_bar_enabled:
                try:
                    self.floating_bar = FloatingBar(self)
                except Exception as e:
                    log_error("floating_bar_create", e)
                    self.floating_bar = None
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
            self.graph_frame.grid(row=1, column=1, sticky="nsew", padx=20, pady=20)
            self.grid_columnconfigure(1, weight=3)
            self.btn_graphs.configure(text="Hide Charts")
        else:
            self.graph_frame.grid_remove()
            self.grid_columnconfigure(1, weight=0)
            self.btn_graphs.configure(text="Show Charts")

    def toggle_silent_tracking(self):
        """Toggle silent tracking mode (track without notifications)."""
        self.silent_tracking = not self.silent_tracking
        if self.silent_tracking:
            self.lbl_status.configure(text="SILENT MODE", text_color=BEE_AMBER_DIM)
            show_notification(
                master=self,
                title="Silent Mode Active",
                message="Tracking continues but notifications are muted.",
                duration=3000,
                color=BEE_AMBER
            )
        else:
            if self.is_paused:
                self.lbl_status.configure(text="PAUSED", text_color=BEE_GOLD)
            elif self.is_tracking:
                self.lbl_status.configure(text="WATCHING", text_color=BEE_GREEN)
            show_notification(
                master=self,
                title="Notifications Restored",
                message="You will receive productivity alerts again.",
                duration=3000,
                color=BEE_GREEN
            )

    def exit_app(self):
        self._destroy_floating_bar()

        if self.is_tracking:
            # Stop tracking, SAVE immediately, update UI, then show summary
            self.is_tracking = False
            
            # Capture stats BEFORE reset
            saved_stats = self.live_stats.copy()
            saved_switches = self.switch_count
            
            try:
                self.save_live_session()  # Save BEFORE showing summary
            except Exception as e:
                log_error("exit_app_save", e)
            
            try:
                self.btn_toggle.configure(text="Start Session", fg_color=BEE_AMBER, hover_color=BEE_AMBER_DIM)
            except Exception:
                pass
            try:
                self.btn_pause.configure(state="disabled", text="Privacy Pause")
            except Exception:
                pass
            try:
                self.lbl_status.configure(text="IDLE", text_color=BEE_GRAY)
                self.dot_status.configure(text="●", text_color=BEE_GRAY)
            except Exception:
                pass
            self.show_session_summary(saved_stats, saved_switches)
        else:
            self.is_tracking = False
            self.quit()
            self.destroy()

    def _create_tray_image(self):
        # Create a simple square icon in memory
        size = (64, 64)
        image = Image.new("RGBA", size, (46, 36, 22, 255))
        draw = ImageDraw.Draw(image)
        draw.ellipse((12, 12, 52, 52), fill=(200, 150, 74, 255))
        return image

    def _minimize_to_tray(self):
        if self._tray_active:
            return
        if getattr(self, "floating_bar_enabled", True) and getattr(self, "floating_bar", None) and self.floating_bar.winfo_exists():
            try:
                self.floating_bar._collapse()
                self.floating_bar.deiconify()
                self.floating_bar.lift()
            except Exception:
                pass
        self.withdraw()
        image = self._create_tray_image()

        def on_restore(icon, item):
            icon.stop()
            self.after(0, self._restore_from_tray)

        def on_exit(icon, item):
            icon.stop()
            self.after(0, self._exit_from_tray)

        menu = pystray.Menu(
            pystray.MenuItem("Restore", on_restore),
            pystray.MenuItem("Exit", on_exit),
        )

        self.tray_icon = pystray.Icon("beeaware", image, "BeeAware", menu)

        def run_icon():
            try:
                self._tray_active = True
                self.tray_icon.run()
            finally:
                self._tray_active = False

        self._tray_thread = threading.Thread(target=run_icon, daemon=True)
        self._tray_thread.start()

    def _restore_from_tray(self):
        try:
            if self.tray_icon:
                # ensure icon stopped
                try:
                    self.tray_icon.stop()
                except Exception:
                    pass
                self.tray_icon = None
        finally:
            self.deiconify()
            self.lift()
            if getattr(self, "floating_bar_enabled", True) and getattr(self, "floating_bar", None) and self.floating_bar.winfo_exists():
                try:
                    self.floating_bar.deiconify()
                    self.floating_bar._collapse()
                    self.floating_bar.lift()
                except Exception:
                    pass

    def _exit_from_tray(self):
        # Prompt to save session before exiting
        try_save = messagebox.askyesno(
            "Save Session?",
            "Save current session before exiting?",
        )
        if try_save:
            self.save_live_session()
        try:
            self.quit()
            self.destroy()
        except Exception:
            pass

    def _on_close_request(self):
        # Ask whether to minimize to tray
        minimize = messagebox.askyesno(
            "Minimize to Tray?",
            "Would you like to minimize to system tray?",
        )
        if minimize:
            try:
                self._minimize_to_tray()
            except Exception as e:
                log_error("minimize_to_tray", e)
                # fallback to normal exit prompt
                proceed = messagebox.askyesno(
                    "Exit",
                    "Minimize failed. Save session and exit?",
                )
                if proceed:
                    self.save_live_session()
                try:
                    self.quit()
                    self.destroy()
                except Exception:
                    pass
        else:
            save = messagebox.askyesno(
                "Save Session?",
                "Save current session before exiting?",
            )
            if save:
                try:
                    self.save_live_session()
                except Exception as e:
                    log_error("save_on_exit", e)
            try:
                self.quit()
                self.destroy()
            except Exception:
                pass

    def show_session_summary(self, saved_stats, saved_switches):
        """Launch the dedicated SessionSummaryWindow with rich visuals."""
        SessionSummaryWindow(self, saved_stats, saved_switches)

    def _resume_from_summary(self, summary_window=None):
        """Resume session after viewing summary."""
        if summary_window:
            summary_window.destroy()
        
        # Restart tracking and UI state
        self.is_tracking = True
        try:
            self.btn_toggle.configure(text="End & Save Session", fg_color=BEE_RED, hover_color="#8f3f30")
        except Exception:
            pass
        try:
            self.btn_pause.configure(state="normal", text="Privacy Pause")
        except Exception:
            pass
        try:
            self.lbl_status.configure(text="WATCHING", text_color=BEE_GREEN)
            self.dot_status.configure(text="●", text_color=BEE_GREEN)
        except Exception:
            pass

        # (Re)start watcher thread if not running
        if not self.tracking_thread or not getattr(self.tracking_thread, "is_alive", lambda: False)():
            self.tracking_thread = threading.Thread(target=self.watcher_loop, daemon=True)
            self.tracking_thread.start()

        self.update_live_ui()

    def _confirm_and_save(self, summary_window):
        """Close app (session already saved in exit_app)."""
        summary_window.destroy()
        try:
            self.quit()
            self.destroy()
        except Exception:
            pass

    # Data persistence 
    def save_live_session(self):
        os.makedirs(os.path.dirname(DAILY_LOG_PATH), exist_ok=True)
        
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # This dictionary will hold our consolidated daily totals
        daily_totals = {} 
        
        try:
            
            if os.path.isfile(DAILY_LOG_PATH):
                with open(DAILY_LOG_PATH, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    header = next(reader, None) 
                    for row in reader:
                        if len(row) < 6: 
                            continue
                        
                        date_str = row[0].split(" ")[0]
                
                        if date_str in daily_totals:
                            daily_totals[date_str][1] += int(row[1])
                            daily_totals[date_str][2] += int(row[2])
                            daily_totals[date_str][3] += int(row[3])
                            daily_totals[date_str][4] += int(row[4])
                            daily_totals[date_str][5] += int(row[5])
                            daily_totals[date_str][0] = row[0] 
                        else:
                     
                            daily_totals[date_str] = [
                                row[0], int(row[1]), int(row[2]), 
                                int(row[3]), int(row[4]), int(row[5])
                            ]
            
           
            if today_str in daily_totals:
                daily_totals[today_str][1] += self.live_stats[0]
                daily_totals[today_str][2] += self.live_stats[1]
                daily_totals[today_str][3] += self.live_stats[2]
                daily_totals[today_str][4] += self.live_stats[3]
                daily_totals[today_str][5] += self.switch_count
                daily_totals[today_str][0] = now_str 
            else:
                daily_totals[today_str] = [
                    now_str, self.live_stats[0], self.live_stats[1], 
                    self.live_stats[2], self.live_stats[3], self.switch_count
                ]
            
            # 3. Write the clean, consolidated log back to the CSV
            with open(DAILY_LOG_PATH, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "q1_urgent", "q2_growth", "q3_noise", "q4_play", "switching_intensity"])
                
                # Sort dates so the log stays chronological
                for date_str in sorted(daily_totals.keys()):
                    writer.writerow(daily_totals[date_str])

        except Exception as e:
            log_error("save_live_session", e)
            
        self.save_app_history()

        # Reset in-memory session state so subsequent sessions start fresh
        try:
            self.live_stats = {0: 0, 1: 0, 2: 0, 3: 0}
            self.app_freq = {}
            self.switch_count = 0
            self.last_window = None
            self.session_start = None
            self.current_window = "Waiting..."
            self.current_exe = ""
            self.current_verdict = "Idle"

            # Update UI if present
            try:
                self.lbl_live_prod.configure(text=self.format_time(0))
                self.lbl_live_dist.configure(text=self.format_time(0))
                for q, lbl in getattr(self, 'q_time_labels', {}).items():
                    lbl.configure(text=self.format_time(0))
                try:
                    self.lbl_switches.configure(text="0")
                except Exception:
                    pass
                try:
                    self.lbl_exe_val.configure(text="—")
                    self.lbl_title_val.configure(text="—")
                    self.lbl_verdict_val.configure(text="Idle")
                except Exception:
                    pass
            except Exception:
                pass
        except Exception as e:
            log_error("reset_after_save", e)

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
                # Midnight boundary check: auto-save and reset if day changed
                current_date = datetime.now().date()
                if self.session_start and current_date != self.session_start.date():
                    self.is_tracking = False
                    self.after(0, lambda: messagebox.showinfo(
                        "Midnight Boundary",
                        "Session crossed into a new day.\nSaving current session..."
                    ))
                    self.save_live_session()
                    self.session_start = datetime.now()
                    self.live_stats = {0: 0, 1: 0, 2: 0, 3: 0}
                    self.switch_count = 0
                    self.is_tracking = True
                
                raw_title = gw.getActiveWindowTitle() or "Desktop"
                hwnd = win32gui.GetForegroundWindow()
                exe_name  = get_active_process_name()
                self.current_window = raw_title
                self.current_exe    = exe_name

                try:
                    _, active_pid = win32process.GetWindowThreadProcessId(hwnd)
                except Exception:
                    active_pid = None

                if self.is_paused:
                    self.current_verdict = "HIDDEN (Privacy Mode)"
                    time.sleep(1)
                    continue

                if raw_title in IDLE_TITLES or exe_name in IDLE_EXES:
                    self.current_verdict = "IDLE / SYSTEM"
                    time.sleep(1)
                    continue

                active_window_key = hwnd or raw_title
                if active_window_key != self.last_window:
                    self.switch_count += 1
                    self.last_window = active_window_key

                normalized_title = raw_title.lower().replace(" ", "").replace("-", "")
                normalized_exe = exe_name.lower().replace(".exe", "").replace(" ", "")

                override = False
                active_q_int = None  # Track the integer value of the active quadrant

                for kw, q in CUSTOM_OVERRIDES.items():
                    if kw in normalized_title or kw in normalized_exe:
                        self.live_stats[q] += 1
                        self.current_verdict = f"{QUADRANTS[q]} (Override)"
                        override = True
                        active_q_int = q
                        break

                if not override:
                    nlp_input = self.build_nlp_input(exe_name, raw_title)
                    # Safe NLP prediction with Q2 fallback
                    pred = self.safe_predict(nlp_input)
                    self.live_stats[pred] += 1
                    self.current_verdict = QUADRANTS[pred]
                    active_q_int = pred

                # --- NOTIFICATION LOGIC ---
                # Decrease cooldown if active
                if self.notifications_enabled and not self.silent_tracking:
                    if self.notif_cooldown > 0:
                        self.notif_cooldown -= 1

                    if self.notif_cooldown == 0:
                        q1_time = self.live_stats[0]
                        q2_time = self.live_stats[1]
                        q3_time = self.live_stats[2]
                        q4_time = self.live_stats[3]
                        productive_time = q1_time + q2_time

                        # 1. Check Q4 (Play) Total Time
                        if q4_time >= self.WARNING_THRESHOLD and q4_time > productive_time:
                            q4_mins = q4_time // 60
                            prod_mins = productive_time // 60
                            
                            msg = (f"You've spent a total of {q4_mins}m in Q4 (Play) this session, "
                                f"compared to only {prod_mins}m on productive tasks. "
                                "Time to shift focus.")
                            
                            self.after(0, lambda: show_notification(
                                master=self,
                                title="Productivity Alert",
                                message=msg,
                                duration=6000,
                                color=BEE_RED
                            ))
                            self.notif_cooldown = 900  # 15-minute cooldown
                        
                        # 2. Check Q3 (Noise) Total Time if Q4 didn't trigger
                        elif q3_time >= self.WARNING_THRESHOLD and q3_time > productive_time:
                            q3_mins = q3_time // 60
                            prod_mins = productive_time // 60
                            
                            msg = (f"You've spent a total of {q3_mins}m in Q3 (Noise) this session, "
                                f"compared to {prod_mins}m on productive tasks. "
                                "Let's get back on track.")
                            
                            self.after(0, lambda m=msg: show_notification(
                                master=self,
                                title="Focus Check",
                                message=m,
                                duration=6000,
                                color=BEE_AMBER
                            ))
                            self.notif_cooldown = 900  # 15-minute cooldown

                # --- APP FREQUENCY TRACKING ---
                # Track app usage regardless of notification settings
                active_q = next(
                    (q for q, name in QUADRANTS.items() if name in self.current_verdict), None
                )
                if active_q is not None:
                    if exe_name not in self.app_freq:
                        self.app_freq[exe_name] = {"seconds": 0, "quadrant_counts": {0: 0, 1: 0, 2: 0, 3: 0}}
                    self.app_freq[exe_name]["seconds"] += 1
                    self.app_freq[exe_name]["quadrant_counts"][active_q] += 1

                time.sleep(1)
            except Exception as e:
                log_error("watcher_loop", e)
                time.sleep(1)

    # Helpers
    def safe_predict(self, nlp_input: str) -> int:
        """
        Safely predict quadrant from NLP input.
        Falls back to Q2 (Deep Work) if vectorizer or model fails.
        This is a safe assumption for a student/professional.
        """
        try:
            if not self.vectorizer or not self.model:
                log_error("safe_predict", "Models not initialized")
                return 1  # Default to Q2 (Growth/Deep Work)
            
            vec = self.vectorizer.transform([nlp_input])
            pred = int(self.model.predict(vec)[0])
            
            # Validate prediction is in valid range [0, 3]
            if pred not in [0, 1, 2, 3]:
                log_error("safe_predict", f"Invalid prediction: {pred}")
                return 1  # Default to Q2
            
            return pred
        except Exception as e:
            log_error("safe_predict", e)
            return 1  # Default to Q2 on any error

    def build_nlp_input(self, exe_name: str, raw_title: str) -> str:
        exe_label = exe_name.lower().replace(".exe", "").strip()
        source_type = "web browser" if exe_name in BROWSER_EXES else "app"
        app_family = self.infer_app_family(exe_label, raw_title)
        browser_category = self.infer_browser_category(raw_title) if source_type == "web browser" else "unknown"
        return f"{exe_label} | {source_type} | {app_family} | {browser_category} | {raw_title}"

    def infer_app_family(self, exe_label: str, raw_title: str) -> str:
        text = f"{exe_label} {raw_title}".lower()
        if any(word in text for word in ["word", "excel", "powerpoint", "office", "outlook", "onenote"]):
            return "office"
        if any(word in text for word in ["vscode", "pycharm", "visualstudio", "ide", "studio", "git", "github", "gitlab"]):
            return "dev"
        if any(word in text for word in ["zoom", "teams", "slack", "discord", "mail", "email", "meet", "calendar"]):
            return "communication"
        if any(word in text for word in ["youtube", "netflix", "spotify", "stream", "music", "video", "movie"]):
            return "media"
        if any(word in text for word in ["game", "play", "arcade", "vr", "steam", "gamer", "quest"]):
            return "game"
        if any(word in text for word in ["docs", "research", "course", "assignment", "study", "tutorial"]):
            return "productivity"
        return "app"

    def infer_browser_category(self, raw_title: str) -> str:
        text = raw_title.lower()
        if any(word in text for word in ["docs", "drive", "slides", "sheets", "office", "outlook"]):
            return "productivity"
        if any(word in text for word in ["meet", "calendar", "hangouts", "gmail", "outlook", "email"]):
            return "communication"
        if any(word in text for word in ["github", "stack overflow", "gitlab", "stackoverflow"]):
            return "dev"
        if any(word in text for word in ["youtube", "netflix", "twitch", "spotify", "video", "music"]):
            return "media"
        if any(word in text for word in ["twitter", "facebook", "reddit", "discord", "instagram"]):
            return "social"
        if any(word in text for word in ["news", "cnn", "nyt", "bbc", "guardian"]):
            return "news"
        return "browser"

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
    
    def open_options(self):
        if self.options_window is None or not self.options_window.winfo_exists():
            self.options_window = OptionsWindow(self, self)  
        else:
            self.options_window.focus()

    def open_history(self):
        if self.history_window is None or not self.history_window.winfo_exists():
            self.history_window = HistoryWindow(self)
        else:
            self.history_window.focus()  