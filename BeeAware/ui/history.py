import os
import pandas as pd
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from config import (
    BEE_AMBER, BEE_AMBER_DIM, BEE_BROWN, BEE_CREAM, BEE_COMB, BEE_COMB_LIGHT,
    BEE_COMB_MID,
    BEE_GRAY, BEE_GREEN, BEE_RED, BEE_GOLD, DAILY_LOG_PATH, APP_HISTORY_PATH,
)
from logger import log_error


class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)

        self.title("Beeware Usage History")
        self.geometry("980x650")
        self.configure(fg_color=BEE_COMB)
        self.resizable(True, True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            self,
            text="Usage History",
            font=("Segoe UI", 20, "bold"),
            text_color=BEE_AMBER,
        )
        header.grid(row=0, column=0, pady=(18, 8), padx=18, sticky="w")

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.tabview.add("Daily Logs")
        self.tabview.add("App History")

        self.daily_tab = self.tabview.tab("Daily Logs")
        self.app_tab = self.tabview.tab("App History")

        self._build_daily_layout()
        self._build_app_layout()

        self._populate_daily_logs()
        self._populate_app_history()

    def _build_daily_layout(self):
        self.daily_tab.grid_columnconfigure(0, weight=0)
        self.daily_tab.grid_columnconfigure(1, weight=1)
        self.daily_tab.grid_rowconfigure(0, weight=1)

        self.daily_list_frame = ctk.CTkScrollableFrame(
            self.daily_tab, fg_color=BEE_COMB_LIGHT, corner_radius=12, width=320
        )
        self.daily_list_frame.grid(row=0, column=0, sticky="nsw", padx=(12, 6), pady=12)

        self.daily_chart_frame = ctk.CTkFrame(
            self.daily_tab, fg_color=BEE_COMB_LIGHT, corner_radius=12
        )
        self.daily_chart_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        self.daily_chart_frame.grid_columnconfigure(0, weight=1)
        self.daily_chart_frame.grid_rowconfigure(0, weight=1)

        self.daily_info_label = ctk.CTkLabel(
            self.daily_chart_frame,
            text="Select a day from the list to view chart details.",
            font=ctk.CTkFont(size=11),
            text_color=BEE_CREAM,
            wraplength=520,
            justify="left",
        )
        self.daily_info_label.grid(row=0, column=0, sticky="nw", padx=16, pady=16)

        self.daily_canvas_container = ctk.CTkFrame(
            self.daily_chart_frame, fg_color="transparent"
        )
        self.daily_canvas_container.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.daily_canvas_container.grid_columnconfigure(0, weight=1)
        self.daily_canvas_container.grid_rowconfigure(0, weight=1)

    def _build_app_layout(self):
        self.app_tab.grid_columnconfigure(0, weight=0)
        self.app_tab.grid_columnconfigure(1, weight=1)
        self.app_tab.grid_rowconfigure(0, weight=1)

        self.app_list_frame = ctk.CTkScrollableFrame(
            self.app_tab, fg_color=BEE_COMB_LIGHT, corner_radius=12, width=320
        )
        self.app_list_frame.grid(row=0, column=0, sticky="nsw", padx=(12, 6), pady=12)

        self.app_chart_frame = ctk.CTkFrame(
            self.app_tab, fg_color=BEE_COMB_LIGHT, corner_radius=12
        )
        self.app_chart_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        self.app_chart_frame.grid_columnconfigure(0, weight=1)
        self.app_chart_frame.grid_rowconfigure(0, weight=1)

        self.app_info_label = ctk.CTkLabel(
            self.app_chart_frame,
            text="Select a session from the list to view app usage chart.",
            font=ctk.CTkFont(size=11),
            text_color=BEE_CREAM,
            wraplength=520,
            justify="left",
        )
        self.app_info_label.grid(row=0, column=0, sticky="nw", padx=16, pady=16)

        self.app_canvas_container = ctk.CTkFrame(
            self.app_chart_frame, fg_color="transparent"
        )
        self.app_canvas_container.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.app_canvas_container.grid_columnconfigure(0, weight=1)
        self.app_canvas_container.grid_rowconfigure(0, weight=1)

    def _populate_daily_logs(self):
        for widget in self.daily_list_frame.winfo_children():
            widget.destroy()

        if not os.path.exists(DAILY_LOG_PATH):
            ctk.CTkLabel(
                self.daily_list_frame,
                text="No daily log file found.",
                font=ctk.CTkFont(size=12),
                text_color=BEE_GRAY,
            ).pack(pady=20, padx=12)
            return

        try:
            df = pd.read_csv(DAILY_LOG_PATH)
            if df.empty:
                raise ValueError("Daily log CSV is empty")

            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df["date"] = df["timestamp"].dt.date
            df = df.dropna(subset=["timestamp"]).sort_values("timestamp", ascending=False)
            df = df.head(20).copy().fillna(0)

            self.daily_rows = []
            for _, row in df.iterrows():
                self.daily_rows.append({
                    "date": str(row["date"]),
                    "timestamp": row["timestamp"],
                    "q1": int(row.get("q1_urgent", 0)),
                    "q2": int(row.get("q2_growth", 0)),
                    "q3": int(row.get("q3_noise", 0)),
                    "q4": int(row.get("q4_play", 0)),
                    "switches": int(row.get("switching_intensity", 0)),
                })

            header = ctk.CTkLabel(
                self.daily_list_frame,
                text=f"Last {len(self.daily_rows)} days",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=BEE_AMBER,
            )
            header.pack(anchor="w", pady=(12, 8), padx=12)

            for index, entry in enumerate(self.daily_rows):
                label = f"{entry['date']} — Q1:{entry['q1']} Q2:{entry['q2']} Q3:{entry['q3']} Q4:{entry['q4']}"
                button = ctk.CTkButton(
                    self.daily_list_frame,
                    text=label,
                    fg_color=BEE_COMB,
                    hover_color=BEE_COMB_MID,
                    text_color=BEE_CREAM,
                    anchor="w",
                    width=280,
                    command=lambda idx=index: self._select_daily_entry(idx),
                )
                button.pack(fill="x", padx=12, pady=4)

            self._select_daily_entry(0)

        except Exception as e:
            log_error("_populate_daily_logs", e)
            ctk.CTkLabel(
                self.daily_list_frame,
                text="Unable to load daily logs.",
                font=ctk.CTkFont(size=12),
                text_color=BEE_RED,
            ).pack(pady=20, padx=12)

    def _select_daily_entry(self, index: int):
        entry = self.daily_rows[index]
        total = entry["q1"] + entry["q2"] + entry["q3"] + entry["q4"]
        self.daily_info_label.configure(
            text=(
                f"{entry['date']} — Total {self._format_seconds(total)} "
                f"(switches: {entry['switches']})\n"
                f"Q1: {entry['q1']}s, Q2: {entry['q2']}s, Q3: {entry['q3']}s, Q4: {entry['q4']}s"
            )
        )
        self._draw_daily_chart(entry)

    def _draw_daily_chart(self, entry: dict):
        for child in self.daily_canvas_container.winfo_children():
            child.destroy()

        values = [entry["q1"], entry["q2"], entry["q3"], entry["q4"]]
        labels = ["Q1", "Q2", "Q3", "Q4"]
        colors = [BEE_RED, BEE_GREEN, BEE_AMBER, BEE_GOLD]

        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(6.5, 3.2), dpi=100)
        fig.patch.set_facecolor(BEE_COMB_LIGHT)
        ax.set_facecolor(BEE_COMB_LIGHT)

        ax.bar(labels, values, color=colors, edgecolor=BEE_CREAM)
        for i, value in enumerate(values):
            ax.text(i, value + max(5, value * 0.03), f"{self._format_seconds(value)}",
                    ha="center", va="bottom", color=BEE_CREAM, fontsize=9)

        ax.set_title(f"Quadrant Breakdown — {entry['date']}", color=BEE_CREAM, pad=12)
        ax.set_ylabel("Seconds", color=BEE_CREAM)
        ax.tick_params(axis="x", colors=BEE_CREAM)
        ax.tick_params(axis="y", colors=BEE_CREAM)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(BEE_CREAM)
        ax.spines["bottom"].set_color(BEE_CREAM)

        fig.tight_layout(pad=1.5)
        canvas = FigureCanvasTkAgg(fig, master=self.daily_canvas_container)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        plt.close(fig)

    def _populate_app_history(self):
        for widget in self.app_list_frame.winfo_children():
            widget.destroy()

        if not os.path.exists(APP_HISTORY_PATH):
            ctk.CTkLabel(
                self.app_list_frame,
                text="No app history file found.",
                font=ctk.CTkFont(size=12),
                text_color=BEE_GRAY,
            ).pack(pady=20, padx=12)
            return

        try:
            df = pd.read_csv(APP_HISTORY_PATH)
            if df.empty:
                raise ValueError("App history CSV is empty")

            df["session_ts"] = pd.to_datetime(df["session_ts"], errors="coerce")
            history = df.dropna(subset=["session_ts"]).sort_values("session_ts", ascending=False)
            self.session_groups = []
            for session_ts, group in history.groupby("session_ts"):
                total = group["total_seconds"].sum()
                self.session_groups.append({
                    "session_ts": session_ts,
                    "total": int(total),
                    "count": len(group),
                    "data": group.copy(),
                })

            header = ctk.CTkLabel(
                self.app_list_frame,
                text=f"Last {len(self.session_groups)} sessions",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=BEE_AMBER,
            )
            header.pack(anchor="w", pady=(12, 8), padx=12)

            for index, session in enumerate(self.session_groups):
                label = f"{session['session_ts'].strftime('%Y-%m-%d %H:%M:%S')} — {self._format_seconds(session['total'])}"
                button = ctk.CTkButton(
                    self.app_list_frame,
                    text=label,
                    fg_color=BEE_COMB,
                    hover_color=BEE_COMB_MID,
                    text_color=BEE_CREAM,
                    anchor="w",
                    width=280,
                    command=lambda idx=index: self._select_app_session(idx),
                )
                button.pack(fill="x", padx=12, pady=4)

            self._select_app_session(0)

        except Exception as e:
            log_error("_populate_app_history", e)
            ctk.CTkLabel(
                self.app_list_frame,
                text="Unable to load app history.",
                font=ctk.CTkFont(size=12),
                text_color=BEE_RED,
            ).pack(pady=20, padx=12)

    def _select_app_session(self, index: int):
        session = self.session_groups[index]
        self.app_info_label.configure(
            text=(
                f"Session: {session['session_ts'].strftime('%Y-%m-%d %H:%M:%S')} — "
                f"{self._format_seconds(session['total'])} total across {session['count']} apps."
            )
        )
        self._draw_app_history_chart(session)

    def _draw_app_history_chart(self, session: dict):
        for child in self.app_canvas_container.winfo_children():
            child.destroy()

        group = session["data"].copy()
        group = group.sort_values("total_seconds", ascending=False).head(12)

        labels = [str(app).replace(".exe", "") for app in group["exe_name"]]
        values = [int(v) for v in group["total_seconds"]]
        colors = [BEE_GREEN if q == 1 else BEE_RED if q == 0 else BEE_AMBER if q == 2 else BEE_GOLD for q in group["dominant_q"]]

        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(6.5, 3.8), dpi=100)
        fig.patch.set_facecolor(BEE_COMB_LIGHT)
        ax.set_facecolor(BEE_COMB_LIGHT)

        y_pos = range(len(labels))
        ax.barh(y_pos, values, color=colors, edgecolor=BEE_CREAM)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, color=BEE_CREAM, fontsize=9)
        ax.invert_yaxis()

        for i, value in enumerate(values):
            ax.text(value + max(5, value * 0.02), i, self._format_seconds(value),
                    va="center", color=BEE_CREAM, fontsize=8)

        ax.set_title("Top apps this session", color=BEE_CREAM, pad=12)
        ax.xaxis.set_visible(False)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(BEE_CREAM)
        ax.spines["bottom"].set_color(BEE_CREAM)

        fig.tight_layout(pad=1.2)
        canvas = FigureCanvasTkAgg(fig, master=self.app_canvas_container)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        plt.close(fig)

    @staticmethod
    def _format_seconds(value):
        try:
            secs = int(value)
            mins, secs = divmod(secs, 60)
            return f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"
        except Exception:
            return "0s"
