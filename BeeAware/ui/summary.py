import os
import csv
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta

from config import (
    BEE_AMBER, BEE_AMBER_DIM, BEE_BROWN, BEE_CREAM, BEE_COMB, BEE_COMB_LIGHT,
    BEE_COMB_MID, BEE_GRAY, BEE_GREEN, BEE_RED, BEE_GOLD, 
    QUADRANTS, Q_COLORS, DAILY_LOG_PATH,
)
from logger import log_error


class SessionSummaryWindow(ctk.CTkToplevel):
    def __init__(self, master, saved_stats, saved_switches):
        super().__init__(master)
        
        self.title("Session Summary — Beeware")
        self.geometry("900x700")
        self.configure(fg_color=BEE_COMB)
        self.resizable(True, True)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        
        self.saved_stats = saved_stats
        self.saved_switches = saved_switches
        
        # Title
        title = ctk.CTkLabel(
            self,
            text="📊 Session Summary — Saved!",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=BEE_GREEN,
        )
        title.grid(row=0, column=0, pady=(16, 8), padx=16, sticky="w")
        
        # Main content frame (scrollable)
        scroll_frame = ctk.CTkScrollableFrame(self, fg_color=BEE_COMB)
        scroll_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        scroll_frame.grid_columnconfigure((0, 1), weight=1)
        
        # --- Session Summary (left column) ---
        self._build_session_summary(scroll_frame)
        
        # --- Comparison (right column) ---
        self._build_comparison(scroll_frame)
        
        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color=BEE_COMB)
        btn_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        btn_frame.grid_columnconfigure(0, weight=1)
        
        btn_resume = ctk.CTkButton(
            btn_frame,
            text="Resume Session",
            fg_color=BEE_AMBER,
            hover_color=BEE_AMBER_DIM,
            command=lambda: self._resume_action(master)
        )
        btn_resume.pack(side="left", padx=4)
        
        btn_exit = ctk.CTkButton(
            btn_frame,
            text="Exit",
            fg_color=BEE_RED,
            hover_color="#8f3f30",
            command=self.destroy
        )
        btn_exit.pack(side="right", padx=4)
    
    def _build_session_summary(self, parent):
        """Build left panel with session totals and pie chart."""
        frame = ctk.CTkFrame(parent, fg_color=BEE_COMB_LIGHT, corner_radius=12)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=8)
        frame.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkLabel(
            frame,
            text="This Session",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=BEE_GOLD,
        )
        header.pack(pady=(12, 8), padx=12, anchor="w")
        
        # Total time
        total_secs = sum(self.saved_stats.values())
        total_str = self._format_seconds(total_secs)
        lbl_total = ctk.CTkLabel(
            frame,
            text=f"Total: {total_str}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=BEE_CREAM,
        )
        lbl_total.pack(pady=(4, 12), padx=12, anchor="w")
        
        # Quadrant breakdown
        quad_frame = ctk.CTkFrame(frame, fg_color=BEE_COMB_MID, corner_radius=8)
        quad_frame.pack(fill="x", padx=12, pady=(0, 12))
        quad_frame.grid_columnconfigure(0, weight=1)
        
        quadrant_names = ["Q1 (Urgent)", "Q2 (Deep Work)", "Q3 (Noise)", "Q4 (Play)"]
        for q, name in enumerate(quadrant_names):
            time_str = self._format_seconds(self.saved_stats[q])
            color = list(Q_COLORS.values())[q] if q < len(Q_COLORS) else BEE_CREAM
            
            # Row with label and value
            row_frame = ctk.CTkFrame(quad_frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=12, pady=6)
            row_frame.grid_columnconfigure(0, weight=1)
            
            lbl_name = ctk.CTkLabel(
                row_frame,
                text=name,
                font=ctk.CTkFont(size=11),
                text_color=BEE_GRAY,
            )
            lbl_name.grid(row=0, column=0, sticky="w")
            
            lbl_val = ctk.CTkLabel(
                row_frame,
                text=time_str,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=color,
            )
            lbl_val.grid(row=0, column=1, sticky="e")
        
        # Switches
        switch_frame = ctk.CTkFrame(quad_frame, fg_color="transparent")
        switch_frame.pack(fill="x", padx=12, pady=6)
        switch_frame.grid_columnconfigure(0, weight=1)
        
        lbl_switch_name = ctk.CTkLabel(
            switch_frame,
            text="Window Switches",
            font=ctk.CTkFont(size=11),
            text_color=BEE_GRAY,
        )
        lbl_switch_name.grid(row=0, column=0, sticky="w")
        
        lbl_switch_val = ctk.CTkLabel(
            switch_frame,
            text=str(self.saved_switches),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=BEE_CREAM,
        )
        lbl_switch_val.grid(row=0, column=1, sticky="e")
        
        # Pie chart
        chart_frame = ctk.CTkFrame(frame, fg_color="transparent")
        chart_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        self._draw_pie_chart(chart_frame, self.saved_stats)
    
    def _build_comparison(self, parent):
        """Build right panel with today vs yesterday comparison."""
        frame = ctk.CTkFrame(parent, fg_color=BEE_COMB_LIGHT, corner_radius=12)
        frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=8)
        frame.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkLabel(
            frame,
            text="Comparison",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=BEE_GOLD,
        )
        header.pack(pady=(12, 8), padx=12, anchor="w")
        
        # Load today and yesterday data
        today_stats, yesterday_stats = self._load_daily_stats()
        
        # Today (cumulative with new session)
        today_total = sum(today_stats.values())
        today_str = self._format_seconds(today_total)
        
        today_box = ctk.CTkFrame(frame, fg_color=BEE_COMB_MID, corner_radius=8)
        today_box.pack(fill="x", padx=12, pady=(0, 8))
        today_box.grid_columnconfigure(0, weight=1)
        
        lbl_today_label = ctk.CTkLabel(
            today_box,
            text="Today (Cumulative)",
            font=ctk.CTkFont(size=11),
            text_color=BEE_GRAY,
        )
        lbl_today_label.pack(pady=(8, 0), padx=12, anchor="w")
        
        lbl_today_val = ctk.CTkLabel(
            today_box,
            text=today_str,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=BEE_GREEN,
        )
        lbl_today_val.pack(pady=(0, 8), padx=12, anchor="w")
        
        # Yesterday
        yesterday_total = sum(yesterday_stats.values())
        yesterday_str = self._format_seconds(yesterday_total)
        
        yesterday_box = ctk.CTkFrame(frame, fg_color=BEE_COMB_MID, corner_radius=8)
        yesterday_box.pack(fill="x", padx=12, pady=(0, 8))
        yesterday_box.grid_columnconfigure(0, weight=1)
        
        lbl_yesterday_label = ctk.CTkLabel(
            yesterday_box,
            text="Yesterday (Total)",
            font=ctk.CTkFont(size=11),
            text_color=BEE_GRAY,
        )
        lbl_yesterday_label.pack(pady=(8, 0), padx=12, anchor="w")
        
        lbl_yesterday_val = ctk.CTkLabel(
            yesterday_box,
            text=yesterday_str,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=BEE_CREAM,
        )
        lbl_yesterday_val.pack(pady=(0, 8), padx=12, anchor="w")
        
        # Difference
        diff_secs = today_total - yesterday_total
        diff_str = self._format_seconds(abs(diff_secs))
        diff_label = "↑ More" if diff_secs > 0 else "↓ Less" if diff_secs < 0 else "—"
        diff_color = BEE_GREEN if diff_secs > 0 else BEE_RED if diff_secs < 0 else BEE_GRAY
        
        diff_box = ctk.CTkFrame(frame, fg_color=BEE_COMB_MID, corner_radius=8)
        diff_box.pack(fill="x", padx=12, pady=(0, 12))
        diff_box.grid_columnconfigure(0, weight=1)
        
        lbl_diff_label = ctk.CTkLabel(
            diff_box,
            text="Difference",
            font=ctk.CTkFont(size=11),
            text_color=BEE_GRAY,
        )
        lbl_diff_label.pack(pady=(8, 0), padx=12, anchor="w")
        
        lbl_diff_val = ctk.CTkLabel(
            diff_box,
            text=f"{diff_label} {diff_str}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=diff_color,
        )
        lbl_diff_val.pack(pady=(0, 8), padx=12, anchor="w")
        
        # Comparison chart (today vs yesterday)
        chart_frame = ctk.CTkFrame(frame, fg_color="transparent")
        chart_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        self._draw_comparison_chart(chart_frame, today_stats, yesterday_stats)
    
    def _draw_pie_chart(self, parent, stats):
        """Draw pie chart for quadrant breakdown."""
        values = [stats[q] for q in range(4)]
        labels = [f"Q{q+1}\n{self._format_seconds(values[q])}" for q in range(4)]
        colors = [list(Q_COLORS.values())[q] for q in range(4)]
        
        # Filter out zero values for cleaner display
        non_zero_idx = [i for i, v in enumerate(values) if v > 0]
        if not non_zero_idx:
            # If all zeros, show a neutral message
            lbl = ctk.CTkLabel(
                parent,
                text="No tracked time this session",
                font=ctk.CTkFont(size=12),
                text_color=BEE_GRAY,
            )
            lbl.pack(pady=20)
            return
        
        filtered_values = [values[i] for i in non_zero_idx]
        filtered_labels = [labels[i] for i in non_zero_idx]
        filtered_colors = [colors[i] for i in non_zero_idx]
        
        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(4.5, 3.5), dpi=100)
        fig.patch.set_facecolor(BEE_COMB_LIGHT)
        
        wedges, texts, autotexts = ax.pie(
            filtered_values,
            labels=filtered_labels,
            colors=filtered_colors,
            autopct="%1.1f%%",
            startangle=90,
            textprops=dict(color=BEE_CREAM, fontsize=9),
        )
        
        for autotext in autotexts:
            autotext.set_color(BEE_COMB)
            autotext.set_weight("bold")
        
        ax.set_title("Quadrant Distribution", color=BEE_CREAM, pad=10, fontsize=11, weight="bold")
        
        fig.tight_layout(pad=0.5)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)
    
    def _draw_comparison_chart(self, parent, today_stats, yesterday_stats):
        """Draw bar chart comparing today vs yesterday by quadrant."""
        today_values = [today_stats[q] for q in range(4)]
        yesterday_values = [yesterday_stats[q] for q in range(4)]
        quadrant_labels = ["Q1", "Q2", "Q3", "Q4"]
        
        x = range(len(quadrant_labels))
        width = 0.35
        
        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(4.5, 3.5), dpi=100)
        fig.patch.set_facecolor(BEE_COMB_LIGHT)
        ax.set_facecolor(BEE_COMB_LIGHT)
        
        bars1 = ax.bar([i - width/2 for i in x], today_values, width, label="Today", color=BEE_GREEN, edgecolor=BEE_CREAM)
        bars2 = ax.bar([i + width/2 for i in x], yesterday_values, width, label="Yesterday", color=BEE_GRAY, edgecolor=BEE_CREAM)
        
        ax.set_ylabel("Seconds", color=BEE_CREAM, fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels(quadrant_labels, color=BEE_CREAM, fontsize=9)
        ax.tick_params(axis="y", colors=BEE_CREAM)
        ax.legend(loc="upper left", framealpha=0.9)
        ax.set_title("Today vs Yesterday", color=BEE_CREAM, pad=10, fontsize=11, weight="bold")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(BEE_CREAM)
        ax.spines["bottom"].set_color(BEE_CREAM)
        
        fig.tight_layout(pad=0.5)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)
    
    def _load_daily_stats(self):
        """Load today and yesterday stats from CSV."""
        today_stats = {0: 0, 1: 0, 2: 0, 3: 0}
        yesterday_stats = {0: 0, 1: 0, 2: 0, 3: 0}
        
        if not os.path.exists(DAILY_LOG_PATH):
            return today_stats, yesterday_stats
        
        try:
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            with open(DAILY_LOG_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        row_date = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S").date()
                        if row_date == today:
                            today_stats[0] += int(row.get("q1_urgent", 0))
                            today_stats[1] += int(row.get("q2_growth", 0))
                            today_stats[2] += int(row.get("q3_noise", 0))
                            today_stats[3] += int(row.get("q4_play", 0))
                        elif row_date == yesterday:
                            yesterday_stats[0] += int(row.get("q1_urgent", 0))
                            yesterday_stats[1] += int(row.get("q2_growth", 0))
                            yesterday_stats[2] += int(row.get("q3_noise", 0))
                            yesterday_stats[3] += int(row.get("q4_play", 0))
                    except Exception:
                        continue
        except Exception as e:
            log_error("load_daily_stats", e)
        
        return today_stats, yesterday_stats
    
    def _format_seconds(self, value):
        """Format seconds as human-readable time."""
        try:
            secs = int(value)
            hours, remainder = divmod(secs, 3600)
            mins, secs = divmod(remainder, 60)
            if hours > 0:
                return f"{hours}h {mins}m {secs:02d}s"
            elif mins > 0:
                return f"{mins}m {secs:02d}s"
            else:
                return f"{secs}s"
        except Exception:
            return "0s"
    
    def _resume_action(self, master):
        """Callback to resume session in main app."""
        if hasattr(master, "_resume_from_summary"):
            self.destroy()
            master._resume_from_summary(self)
        else:
            self.destroy()
