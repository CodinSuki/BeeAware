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


class BeewareApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Beeware | Live Productivity Engine")
        self.geometry("1280x780")
        self.configure(fg_color=BEE_COMB)

        self.grid_rowconfigure(1, weight=1)
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

        self.current_window  = "Waiting..."
        self.current_verdict = "Idle"
        self.current_exe     = ""
        self.graph_tick = 0

        try:
            with open('models/V2eisenhower_model.pkl', 'rb') as f:
                self.model = pickle.load(f)
            with open('models/V2tfidf_vectorizer.pkl', 'rb') as f:
                self.vectorizer = pickle.load(f)
            self.ai_status = "✦ AI Models Loaded"
        except Exception as e:
            print(f"Model load error: {e}")
            self.ai_status = "✦ ERROR: Models missing!"

        self.today_stats, self.yesterday_stats = self.load_data()

        self.build_control_panel()
        self.build_monitor_panel()
        self.build_graphs_panel()

        self.protocol("WM_DELETE_WINDOW", self.exit_app)

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
            print(f"Load error: {e}")
            self.last_date_str = "Error"
            return empty_stats, empty_stats

    def toggle_tracking(self):
        if not self.is_tracking:
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
            self.btn_graphs.configure(text="Hide Charts ▲")
        else:
            self.graph_frame.grid_remove()
            self.grid_columnconfigure(1, weight=0)
            self.btn_graphs.configure(text="Show Charts ▼")

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
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['timestamp', 'q1_urgent', 'q2_growth', 'q3_noise', 'q4_play', 'switching_intensity'])
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                self.live_stats[0], self.live_stats[1], self.live_stats[2], self.live_stats[3],
                self.switch_count
            ])

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

                if raw_title in ["Desktop", "Task Manager", "Program Manager", "Settings"] or exe_name == "explorer.exe":
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

            except Exception as e:
                print(f"Watcher error: {e}")

            time.sleep(1)

    def get_active_process_name(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).name().lower()
        except Exception as e:
            print(f"Process name error: {e}")
            return "unknown.exe"

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
            print(f"UI update error: {e}")

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
            font=ctk.CTkFont(size=11), text_color=BEE_GRAY
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

    def build_graphs_panel(self):
        self.graph_frame = ctk.CTkFrame(self, corner_radius=15, fg_color=BEE_COMB_LIGHT)
        self.graph_frame.grid(row=1, column=1, padx=(10, 20), pady=16, sticky="nsew")
        self.refresh_graphs()

    def refresh_graphs(self):
        for widget in self.graph_frame.winfo_children():
            widget.destroy()

        plt.style.use('dark_background')
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4), dpi=100)
        fig.patch.set_facecolor(BEE_COMB_LIGHT)
        ax1.set_facecolor(BEE_COMB_LIGHT)
        ax2.set_facecolor(BEE_COMB_LIGHT)

        colors     = [BEE_RED, BEE_GREEN, BEE_AMBER, BEE_GOLD]
        labels     = ['Q1', 'Q2', 'Q3', 'Q4']
        text_props = {'color': BEE_CREAM, 'fontsize': 9}

        y_sizes = list(self.yesterday_stats.values())
        if sum(y_sizes) > 0:
            _, texts, autotexts = ax1.pie(
                y_sizes, labels=labels, colors=colors,
                autopct='%1.0f%%', startangle=140,
                textprops=text_props
            )
            for at in autotexts:
                at.set_color(BEE_COMB)
                at.set_fontsize(8)
            ax1.set_title(f"Latest Session ({self.last_date_str})", color=BEE_CREAM, pad=12)
        else:
            ax1.text(0.5, 0.5, "No Historical Data", ha='center', va='center', color=BEE_GRAY)
            ax1.axis('off')

        t_sizes = [self.live_stats[q] for q in range(4)] if self.is_tracking else list(self.today_stats.values())
        if sum(t_sizes) > 0:
            _, texts, autotexts = ax2.pie(
                t_sizes, labels=labels, colors=colors,
                autopct='%1.1f%%', startangle=140,
                textprops=text_props
            )
            for at in autotexts:
                at.set_color(BEE_COMB)
                at.set_fontsize(8)
            ax2.set_title("Today's Total", color=BEE_CREAM, pad=12)
        else:
            ax2.text(0.5, 0.5, "No Data Today Yet", ha='center', va='center', color=BEE_GRAY)
            ax2.axis('off')

        fig.tight_layout(pad=2.0)
        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        plt.close(fig)


if __name__ == "__main__":
    app = BeewareApp()
    app.mainloop()
    try:
        app.destroy()
    except Exception:
        pass
