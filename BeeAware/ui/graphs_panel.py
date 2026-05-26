# ui/graphs_panel.py
# Mixin providing build_graphs_panel(), refresh_graphs(),
# _switch_chart_view(), _draw_pie_view(), _draw_bar_view() for BeewareApp.

import os
import customtkinter as ctk
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from config import (
    BEE_AMBER, BEE_AMBER_DIM, BEE_COMB, BEE_COMB_LIGHT, BEE_COMB_MID,
    BEE_BROWN, BEE_CREAM, BEE_GRAY, BEE_RED, BEE_GREEN, BEE_GOLD,
    APP_HISTORY_PATH,
)
from logger import log_error


class GraphsPanelMixin:

    def build_graphs_panel(self):
        self.graph_frame = ctk.CTkFrame(self, corner_radius=15, fg_color=BEE_COMB_LIGHT)
        self.graph_frame.grid(row=1, column=1, padx=(10, 20), pady=16, sticky="nsew")
        self.graph_frame.grid_rowconfigure(1, weight=1)
        self.graph_frame.grid_columnconfigure(0, weight=1)

        # Toggle button row 
        toggle_row = ctk.CTkFrame(self.graph_frame, fg_color="transparent")
        toggle_row.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 0))

        self.btn_view_pie = ctk.CTkButton(
            toggle_row, text="Pie Charts", width=120, height=28,
            fg_color=BEE_AMBER, hover_color=BEE_AMBER_DIM, text_color=BEE_COMB,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self._switch_chart_view("pie"),
        )
        self.btn_view_pie.pack(side="left", padx=(0, 6))

        self.btn_view_bar = ctk.CTkButton(
            toggle_row, text="App Bar Chart", width=130, height=28,
            fg_color=BEE_COMB_MID, hover_color=BEE_BROWN, text_color=BEE_CREAM,
            font=ctk.CTkFont(size=12),
            command=lambda: self._switch_chart_view("bar"),
        )
        self.btn_view_bar.pack(side="left")

        # Canvas container 
        self.chart_canvas_frame = ctk.CTkFrame(self.graph_frame, fg_color="transparent")
        self.chart_canvas_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        self.refresh_graphs()

    def _switch_chart_view(self, view: str):
        """Toggle between pie and bar views, updating button active states."""
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
        """Dual-pie layout: last session (left) vs today (right)."""
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
                autopct="%1.0f%%", startangle=140, textprops=text_props,
            )
            for at in autotexts:
                at.set_color(BEE_COMB)
                at.set_fontsize(8)
            ax1.set_title(f"Latest Session ({self.last_date_str})", color=BEE_CREAM, pad=12)
        else:
            ax1.text(0.5, 0.5, "No Historical Data", ha="center", va="center", color=BEE_GRAY)
            ax1.axis("off")

        t_sizes = (
            [self.live_stats[q] for q in range(4)]
            if self.is_tracking
            else list(self.today_stats.values())
        )
        if sum(t_sizes) > 0:
            _, _, autotexts = ax2.pie(
                t_sizes, labels=labels, colors=colors,
                autopct="%1.1f%%", startangle=140, textprops=text_props,
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
        Data source:
          • Live session  → self.app_freq (in-memory)
          • Idle          → most recent session_ts block from APP_HISTORY_PATH
        Top 10 apps by total seconds, most-used at the top.
        """
        app_data = {}

        if self.is_tracking and self.app_freq:
            for exe, data in self.app_freq.items():
                app_data[exe] = dict(data["quadrant_counts"])
        elif os.path.exists(APP_HISTORY_PATH):
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

        sorted_apps = sorted(app_data.items(), key=lambda x: sum(x[1].values()), reverse=True)[:10]
        sorted_apps = list(reversed(sorted_apps))   # most-used at top of horizontal chart

        exe_labels = [a[0].replace(".exe", "") for a in sorted_apps]
        q_seconds  = [[a[1].get(q, 0) for a in sorted_apps] for q in range(4)]
        q_colors   = [BEE_RED, BEE_GREEN, BEE_AMBER, BEE_GOLD]
        q_names    = ["Q1: Urgent", "Q2: Growth", "Q3: Noise", "Q4: Play"]

        y_pos = range(len(exe_labels))
        lefts = [0] * len(exe_labels)

        for q in range(4):
            vals = q_seconds[q]
            bars = ax.barh(y_pos, vals, left=lefts,
                           color=q_colors[q], label=q_names[q], height=0.6, alpha=0.92)
            for bar, val in zip(bars, vals):
                if val > 30:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_y() + bar.get_height() / 2,
                        f"{val // 60}m" if val >= 60 else f"{val}s",
                        ha="center", va="center",
                        fontsize=7, color=BEE_COMB, fontweight="bold",
                    )
            lefts = [l + v for l, v in zip(lefts, vals)]

        for i, (_, qdata) in enumerate(sorted_apps):
            total = sum(qdata.values())
            mins, secs = divmod(total, 60)
            label = f" {mins}m {secs:02d}s" if mins > 0 else f" {secs}s"
            ax.text(lefts[i] + 1, i, label, va="center", fontsize=8, color=BEE_CREAM)

        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(exe_labels, color=BEE_CREAM, fontsize=9)
        ax.xaxis.set_visible(False)
        for spine in ["top", "right", "bottom"]:
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_color(BEE_BROWN)
        ax.tick_params(axis="y", colors=BEE_CREAM, length=0)

        title = "App Usage — Live Session" if self.is_tracking else "App Usage — Last Session"
        ax.set_title(title, color=BEE_CREAM, pad=10, fontsize=11)
        ax.legend(loc="lower right", fontsize=8, facecolor=BEE_COMB_MID,
                  edgecolor=BEE_BROWN, labelcolor=BEE_CREAM, framealpha=0.9)

        fig.tight_layout(pad=1.5)
        canvas = FigureCanvasTkAgg(fig, master=self.chart_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=6)
        plt.close(fig)
