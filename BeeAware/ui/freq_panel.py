# ui/freq_panel.py
# Mixin providing build_app_freq_panel() and update_app_freq_panel()
# for BeewareApp. Shows most/least used apps with Q badges, live or historical.

import os
import pandas as pd
import customtkinter as ctk

from config import (
    BEE_GOLD, BEE_COMB_LIGHT, BEE_COMB_MID, BEE_GRAY,
    BEE_GREEN, BEE_RED, BEE_CREAM, BEE_AMBER, BEE_COMB,
    APP_HISTORY_PATH,
)
from logger import log_error

Q_BADGE_COLORS = {0: BEE_RED, 1: BEE_GREEN, 2: BEE_AMBER, 3: BEE_GOLD}
Q_BADGE_LABELS = {0: "Q1", 1: "Q2", 2: "Q3", 3: "Q4"}


class FreqPanelMixin:

    def build_app_freq_panel(self):
        """
        Fixed-height panel spanning both columns at row 2.
        Left column: Most Used (top 3). Right column: Least Used (bottom 3).
        Slots are built once at startup; update_app_freq_panel() refreshes labels only.
        """
        self.freq_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=BEE_COMB_LIGHT)
        self.freq_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 14), sticky="ew")
        self.freq_frame.grid_columnconfigure(0, weight=1)
        self.freq_frame.grid_columnconfigure(1, weight=1)

        # Header 
        header = ctk.CTkFrame(self.freq_frame, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 4))

        ctk.CTkLabel(
            header, text="App Frequency",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=BEE_GOLD,
        ).pack(side="left")

        self.lbl_freq_source = ctk.CTkLabel(
            header, text="— no session yet —",
            font=ctk.CTkFont(size=10), text_color=BEE_GRAY,
        )
        self.lbl_freq_source.pack(side="left", padx=10)

        #  Build columns 
        self.most_used_rows  = self._build_freq_column(col=0, label="▲  Most Used",  color=BEE_GREEN)
        self.least_used_rows = self._build_freq_column(col=1, label="▼  Least Used", color=BEE_RED)

    def _build_freq_column(self, col: int, label: str, color: str):
        """Build one Most/Least column with 3 pre-built app slots. Returns list of (badge, name, time) tuples."""
        container = ctk.CTkFrame(self.freq_frame, fg_color=BEE_COMB_MID, corner_radius=8)
        container.grid(
            row=1, column=col,
            padx=(12 if col == 0 else 6, 6 if col == 0 else 12),
            pady=(0, 10), sticky="nsew",
        )
        container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            container, text=label,
            font=ctk.CTkFont(size=11, weight="bold"), text_color=color,
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 4))

        rows = []
        for i in range(3):
            row_frame = ctk.CTkFrame(container, fg_color="transparent")
            row_frame.grid(row=i + 1, column=0, sticky="ew", padx=8, pady=2)
            row_frame.grid_columnconfigure(1, weight=1)

            badge = ctk.CTkLabel(
                row_frame, text="Q?", width=36, height=20,
                fg_color=BEE_GRAY, corner_radius=4,
                font=ctk.CTkFont(size=9, weight="bold"), text_color=BEE_COMB,
            )
            badge.grid(row=0, column=0, padx=(0, 6))

            name_lbl = ctk.CTkLabel(
                row_frame, text="—",
                font=ctk.CTkFont(size=11), text_color=BEE_CREAM, anchor="w",
            )
            name_lbl.grid(row=0, column=1, sticky="w")

            time_lbl = ctk.CTkLabel(
                row_frame, text="",
                font=ctk.CTkFont(size=10), text_color=BEE_GRAY, anchor="e",
            )
            time_lbl.grid(row=0, column=2, sticky="e", padx=(6, 0))

            rows.append((badge, name_lbl, time_lbl))

        ctk.CTkLabel(container, text="", height=6).grid(row=4, column=0)
        return rows

    def update_app_freq_panel(self):
        """
        Refresh most/least rows from live app_freq or APP_HISTORY_PATH.
        Called every second during a session via update_live_ui().
        Blanks unused slots cleanly so stale data never shows.
        """
        most, least = [], []

        if self.is_tracking and self.app_freq:
            most, least = self.get_app_freq_summary(top_n=3)
            self.lbl_freq_source.configure(text="live session", text_color=BEE_GREEN)

        elif os.path.exists(APP_HISTORY_PATH):
            try:
                df = pd.read_csv(APP_HISTORY_PATH)
                if not df.empty:
                    latest_ts = df["session_ts"].max()
                    df = df[df["session_ts"] == latest_ts].copy()
                    df["total_seconds"] = df[["q1_seconds", "q2_seconds",
                                              "q3_seconds", "q4_seconds"]].sum(axis=1)
                    df_sorted = df.sort_values("total_seconds", ascending=False)

                    all_apps = [
                        (row["exe_name"], int(row["total_seconds"]), int(row["dominant_q"]))
                        for _, row in df_sorted.iterrows()
                    ]
                    most  = all_apps[:3]
                    least = all_apps[-3:][::-1] if len(all_apps) > 3 else []
                    self.lbl_freq_source.configure(
                        text=f"last session  ({latest_ts[:10]})", text_color=BEE_GRAY,
                    )
                else:
                    self.lbl_freq_source.configure(text="no history yet", text_color=BEE_GRAY)
            except Exception as e:
                log_error("update_app_freq_panel", e)
        else:
            self.lbl_freq_source.configure(text="— no session yet —", text_color=BEE_GRAY)

        self._fill_freq_rows(self.most_used_rows,  most)
        self._fill_freq_rows(self.least_used_rows, least)

    def _fill_freq_rows(self, row_widgets, data):
        """Write app data into pre-built row slots; blank unused slots."""
        for i, (badge, name_lbl, time_lbl) in enumerate(row_widgets):
            if i < len(data):
                exe, secs, dominant_q = data[i]
                mins, s  = divmod(secs, 60)
                time_str = f"{mins}m {s:02d}s" if mins > 0 else f"{s}s"
                badge.configure(
                    text=Q_BADGE_LABELS.get(dominant_q, "Q?"),
                    fg_color=Q_BADGE_COLORS.get(dominant_q, BEE_GRAY),
                )
                name_lbl.configure(text=exe.replace(".exe", "")[:18])
                time_lbl.configure(text=time_str)
            else:
                badge.configure(text="Q?", fg_color=BEE_GRAY)
                name_lbl.configure(text="—")
                time_lbl.configure(text="")
