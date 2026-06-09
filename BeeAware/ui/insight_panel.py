# ui/insight_panel.py
# Refactored Mixin providing build_insight_panel() and update_behavioral_insight_panel()
# for BeeAwareApp. Transforms raw app metrics into actionable behavioral coaching insights.

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


class InsightPanelMixin:

    def build_insight_panel(self):
        """
        Builds a modern 3-column behavioral coaching and insight laboratory deck.
        Column 0: Focus Analytics Summary & Verdict Badge
        Column 1: Deep Analytical Diagnostics (Top Productivity/Distraction Sinks)
        Column 2: Prescriptive Coaching (Actionable Behavioral Roadmap Interventions)
        """
        # Outer Canvas Frame Configuration
        self.insight_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=BEE_COMB_LIGHT)
        self.insight_frame.grid(row=2, column=0, sticky="nsew", padx=(20, 10), pady=(0, 20))
        
        # Grid Configuration (3 Equal Weighted Structural Columns)
        self.insight_frame.grid_columnconfigure(0, weight=1, uniform="equal")
        self.insight_frame.grid_columnconfigure(1, weight=1, uniform="equal")
        self.insight_frame.grid_columnconfigure(2, weight=1, uniform="equal")
        self.insight_frame.grid_rowconfigure(1, weight=1)

        # Bind resize event for dynamic wraplength
        self.insight_frame.bind("<Configure>", self._on_insight_resize)
        self.insight_text_wraplength = 200

        # Dynamic Engine Header Bar
        header = ctk.CTkFrame(self.insight_frame, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            header, text="🐝 BEHAVIORAL COACHING LAB",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=BEE_GOLD,
        ).pack(side="left")

        self.lbl_insight_source = ctk.CTkLabel(
            header, text="— awaiting telemetry —",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=BEE_GRAY,
        )
        self.lbl_insight_source.pack(side="left", padx=12)


        # COLUMN 0: PERFORMANCE VERDICT & TELEMETRY CARD
        self.card_verdict = ctk.CTkFrame(self.insight_frame, fg_color=BEE_COMB_MID, corner_radius=8)
        self.card_verdict.grid(row=1, column=0, padx=(12, 6), pady=(0, 12), sticky="nsew")
        self.card_verdict.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            self.card_verdict, text="SESSION STATUS & VERDICT",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=BEE_GRAY,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        
        # Large State Badge
        self.badge_status = ctk.CTkLabel(
            self.card_verdict, text="ANALYZING", width=160, height=36,
            fg_color=BEE_GRAY, corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=BEE_COMB
        )
        self.badge_status.grid(row=1, column=0, pady=(10, 10))
        
        # Live Performance Index Metric Display
        self.lbl_focus_index = ctk.CTkLabel(
            self.card_verdict, text="Focus Ratio: 0%",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=BEE_CREAM
        )
        self.lbl_focus_index.grid(row=2, column=0, sticky="w", padx=12, pady=4)

        self.lbl_switch_strain = ctk.CTkLabel(
            self.card_verdict, text="Context Swaps: 0",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color=BEE_GRAY
        )
        self.lbl_switch_strain.grid(row=3, column=0, sticky="w", padx=12, pady=(0, 10))

        # COLUMN 1: ANALYTICAL DIAGNOSTICS (TELEMETRY GAP ANALYSIS)
        self.card_diagnostics = ctk.CTkFrame(self.insight_frame, fg_color=BEE_COMB_MID, corner_radius=8)
        self.card_diagnostics.grid(row=1, column=1, padx=6, pady=(0, 12), sticky="nsew")
        self.card_diagnostics.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            self.card_diagnostics, text="APPLICATION INSIGHT LOGS",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=BEE_GRAY,
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        
        # Diagnostics Output Slots (with dynamic wraplength)
        self.lbl_insight_log_1 = ctk.CTkLabel(
            self.card_diagnostics, text="• Collecting telemetry footprint...",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color=BEE_CREAM, justify="left", wraplength=self.insight_text_wraplength, anchor="nw"
        )
        self.lbl_insight_log_1.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        
        self.lbl_insight_log_2 = ctk.CTkLabel(
            self.card_diagnostics, text="• Initializing engine overrides...",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color=BEE_CREAM, justify="left", wraplength=self.insight_text_wraplength, anchor="nw"
        )
        self.lbl_insight_log_2.grid(row=2, column=0, sticky="nsew", padx=12, pady=6)

        # COLUMN 2: PRESCRIPTIVE BEHAVIORAL COACHING LAB
        self.card_coaching = ctk.CTkFrame(self.insight_frame, fg_color=BEE_COMB_MID, corner_radius=8)
        self.card_coaching.grid(row=1, column=2, padx=(6, 12), pady=(0, 12), sticky="nsew")
        self.card_coaching.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            self.card_coaching, text="PRESCRIPTIVE HABIT COACHING",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=BEE_GRAY,
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        
        # Prescription Text Block Handles (with dynamic wraplength)
        self.lbl_coach_title = ctk.CTkLabel(
            self.card_coaching, text="Awaiting Activity Loop...",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=BEE_GOLD, justify="left", wraplength=self.insight_text_wraplength, anchor="nw"
        )
        self.lbl_coach_title.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 2))

        self.lbl_coach_desc = ctk.CTkLabel(
            self.card_coaching, text="Start your tracking run. BeeAware will calculate structural interventions here.",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color=BEE_CREAM, justify="left", wraplength=self.insight_text_wraplength, anchor="nw"
        )
        self.lbl_coach_desc.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 10))

    def _on_insight_resize(self, event):
        """Update text wraplength dynamically based on panel width."""
        # Each card gets roughly 1/3 of the width minus padding
        card_width = max(event.width // 3 - 40, 80)  # Increased minimum to 80
        self.insight_text_wraplength = card_width
        
        # Update all text labels with new wraplength
        for lbl in [self.lbl_insight_log_1, self.lbl_insight_log_2, self.lbl_coach_title, self.lbl_coach_desc]:
            if lbl.winfo_exists():
                lbl.configure(wraplength=card_width)

    def update_behavioral_insight_panel(self):
        """
        Pulls telemetry files, calculates mathematical focus rates, runs threshold rule checks,
        and dynamically alters UI text nodes without thread stalls.
        """
        all_apps = []

        # 1. Pipeline Routing: Read Data Pool
        if self.is_tracking and self.app_freq:
            # Safely fetch all raw data array dumps from main thread memory cache
            summary = [
                (exe, data["seconds"], max(data["quadrant_counts"], key=data["quadrant_counts"].get))
                for exe, data in self.app_freq.items()
            ]
            summary.sort(key=lambda x: x[1], reverse=True)
            all_apps = summary
            self.lbl_insight_source.configure(text="🟢 LIVE COACHING ENGINE ACTIVE", text_color=BEE_GREEN)

        elif os.path.exists(APP_HISTORY_PATH):
            try:
                df = pd.read_csv(APP_HISTORY_PATH)
                if not df.empty:
                    latest_ts = df["session_ts"].max()
                    df = df[df["session_ts"] == latest_ts].copy()
                    df["total_seconds"] = df[["q1_seconds", "q2_seconds", "q3_seconds", "q4_seconds"]].sum(axis=1)
                    df_sorted = df.sort_values("total_seconds", ascending=False)

                    all_apps = [
                        (row["exe_name"], int(row["total_seconds"]), int(row["dominant_q"]))
                        for _, row in df_sorted.iterrows()
                    ]
                    self.lbl_insight_source.configure(
                        text=f"📊 PAST LOG HISTORICAL REVIEW ({latest_ts[:10]})", text_color=BEE_GRAY
                    )
                else:
                    self._reset_insight_panel_to_idle("No database records discovered.")
                    return
            except Exception as e:
                log_error("update_behavioral_insight_panel", e)
                return
        else:
            self._reset_insight_panel_to_idle("Awaiting session engagement loop.")
            return

        if not all_apps:
            self._reset_insight_panel_to_idle("Analyzing initial sequence...")
            return

        # 2. Extract Key Variables for Analytical Parsing
        total_tracked_time = sum(app[1] for app in all_apps)
        
        # Sum work volumes vs chaos/distraction leak volumes
        q1_q2_time = sum(app[1] for app in all_apps if app[2] in [0, 1])  # Urgent/Growth Focus
        q3_q4_time = sum(app[1] for app in all_apps if app[2] in [2, 3])  # Noise/Play Sinks
        
        focus_ratio = (q1_q2_time / total_tracked_time) * 100 if total_tracked_time > 0 else 0
        switches = getattr(self, "switch_count", 0)

        # Update numerical indicators
        self.lbl_focus_index.configure(text=f"Focus Ratio: {focus_ratio:.1f}%")
        self.lbl_switch_strain.configure(text=f"Context Swaps: {switches} switches")

        # 3. Micro-Engine Algorithmic Decision Tree (Heuristics Mapping)
        top_app, top_app_time, top_app_q = all_apps[0]
        top_app_clean = top_app.replace(".exe", "").capitalize()

        # State A: Extreme Fragmentation State (Tab Spammer Pattern)
        if switches > 35 and focus_ratio < 60:
            self.badge_status.configure(text="⚠️ FRAGMENTED", fg_color=BEE_RED, text_color=BEE_CREAM)
            self.lbl_insight_log_1.configure(text=f"• Attention trap identified: Active window swapping indicates hyper-distraction behavior.")
            self.lbl_insight_log_2.configure(text=f"• Major time leak found inside secondary applications.")
            
            self.lbl_coach_title.configure(text="👉 Action Required: Block Shifts", text_color=BEE_RED)
            self.lbl_coach_desc.configure(
                text="Your attention is split across too many concurrent windows. Close all background processes. Commit to a clean single-task block for 20 minutes."
            )

        # State B: Deep Deep Work Focus Core (Optimal Performance)
        elif focus_ratio >= 75 and switches <= 25:
            self.badge_status.configure(text="🎯 HYPER-FOCUS", fg_color=BEE_GREEN, text_color=BEE_COMB)
            self.lbl_insight_log_1.configure(text=f"• Structural target hit! Deep work environment detected.")
            self.lbl_insight_log_2.configure(text=f"• High optimization run: '{top_app_clean}' is dominating total process footprint.")
            
            self.lbl_coach_title.configure(text="🐝 Continuous Momentum Guard", text_color=BEE_GREEN)
            self.lbl_coach_desc.configure(
                text="Excellent cognitive alignment. Protect this workflow sequence. Silence external smartphone apps to protect your flow state over the next hour."
            )

        # State C: Passive Drift State (Social Media or Video Loop Binge)
        elif focus_ratio < 40 and top_app_q == 3:  # Binging Q4 Play apps
            self.badge_status.configure(text="🛑 PASSIVE DRIFT", fg_color=BEE_AMBER, text_color=BEE_COMB)
            self.lbl_insight_log_1.configure(text=f"• High-consumption anomaly: Your system engine is locked into an automated distraction sequence.")
            self.lbl_insight_log_2.configure(text=f"• '{top_app_clean}' has completely consumed your active session distribution.")
            
            self.lbl_coach_title.configure(text="⚡ Intercept Procrastination Loop", text_color=BEE_AMBER)
            self.lbl_coach_desc.configure(
                text="You've slipped into automatic binging loops. Physically minimize this app context right now. Switch to a Q1 task to reset your focus metrics."
            )

        # State D: Default Maintenance Mode
        else:
            self.badge_status.configure(text="⚖️ STABLE RUN", fg_color=BEE_GOLD, text_color=BEE_COMB)
            self.lbl_insight_log_1.configure(text=f"• Operational stability within acceptable boundaries.")
            self.lbl_insight_log_2.configure(text=f"• Core utility balance achieved between work tools and messaging.")
            
            self.lbl_coach_title.configure(text="⏳ Minor Optimization Path", text_color=BEE_GOLD)
            self.lbl_coach_desc.configure(
                text="Your baseline execution is balanced. To step up optimization, try to systematically prune non-essential chat applications down to minimize fatigue."
            )

    def _reset_insight_panel_to_idle(self, reason_text: str):
        """Safely clean elements out when no analytical session framework exists."""
        self.badge_status.configure(text="IDLE", fg_color=BEE_GRAY, text_color=BEE_COMB)
        self.lbl_focus_index.configure(text="Focus Ratio: —")
        self.lbl_switch_strain.configure(text="Context Swaps: —")
        self.lbl_insight_log_1.configure(text=f"• Data pool empty.")
        self.lbl_insight_log_2.configure(text=f"• {reason_text}")
        self.lbl_coach_title.configure(text="Awaiting Initialization Loop...", text_color=BEE_GOLD)
        self.lbl_coach_desc.configure(text="Engage the primary monitoring node toggle. The real-time behavioral coach engine will launch diagnostics automatically.")