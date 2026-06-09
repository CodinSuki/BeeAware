# ui/monitor_panel.py
# Mixin providing build_monitor_panel() and update_live_ui() for BeeAwareApp.

import customtkinter as ctk
from config import (
    BEE_GOLD, BEE_BROWN, BEE_COMB_LIGHT, BEE_COMB_MID,
    BEE_CREAM, BEE_GREEN, BEE_RED, BEE_GRAY, BEE_AMBER_DIM,
    BEE_BROWN, BEE_AMBER, QUADRANTS, Q_COLORS,
)
from logger import log_error
from .correction import CorrectionMixin


class MonitorPanelMixin:

    def build_monitor_panel(self):
        self.monitor_frame = ctk.CTkFrame(self, corner_radius=15, fg_color=BEE_COMB_LIGHT)
        # MEGA SQUEEZE: outer vertical padding reduced to 4
        self.monitor_frame.grid(row=1, column=0, padx=(20, 10), pady=4, sticky="nsew")
        self.monitor_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.monitor_frame, text="Live Monitor",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=BEE_GOLD,
        ).pack(pady=(4, 0)) 

        ctk.CTkLabel(
            self.monitor_frame, text="─" * 28,
            text_color=BEE_BROWN, font=ctk.CTkFont(size=10),
        ).pack(pady=0) 

        # ── Focus / Distracted totals ─────────────────────────────────────────
        totals_frame = ctk.CTkFrame(self.monitor_frame, fg_color=BEE_COMB_MID, corner_radius=10)
        totals_frame.pack(fill="x", padx=16, pady=2) 
        totals_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(totals_frame, text="Focus",
                     font=ctk.CTkFont(size=11), text_color=BEE_GRAY).grid(row=0, column=0, pady=(4, 0))
        ctk.CTkLabel(totals_frame, text="Distracted",
                     font=ctk.CTkFont(size=11), text_color=BEE_GRAY).grid(row=0, column=1, pady=(4, 0))

        self.lbl_live_prod = ctk.CTkLabel(
            totals_frame, text="0m 00s",
            font=ctk.CTkFont(size=20, weight="bold"), text_color=BEE_GREEN,
        )
        self.lbl_live_prod.grid(row=1, column=0, pady=(0, 4))

        self.lbl_live_dist = ctk.CTkLabel(
            totals_frame, text="0m 00s",
            font=ctk.CTkFont(size=20, weight="bold"), text_color=BEE_RED,
        )
        self.lbl_live_dist.grid(row=1, column=1, pady=(0, 4))

        # ── Per-quadrant breakdown ────────────────────────────────────────────
        q_frame = ctk.CTkFrame(self.monitor_frame, fg_color=BEE_COMB_MID, corner_radius=10)
        q_frame.pack(fill="x", padx=16, pady=2) 
        q_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.q_time_labels = {}
        for i, (q, name) in enumerate(QUADRANTS.items()):
            short = name.split(":")[0]
            ctk.CTkLabel(
                q_frame, text=short, font=ctk.CTkFont(size=10), text_color=BEE_GRAY,
            ).grid(row=0, column=i, pady=(2, 0), padx=4)
            lbl = ctk.CTkLabel(
                q_frame, text="0m 00s",
                font=ctk.CTkFont(size=12, weight="bold"), text_color=Q_COLORS[q],
            )
            lbl.grid(row=1, column=i, pady=(0, 2), padx=4)
            self.q_time_labels[q] = lbl

        ctk.CTkLabel(
            self.monitor_frame, text="─" * 28,
            text_color=BEE_BROWN, font=ctk.CTkFont(size=10),
        ).pack(pady=0)

        # ── Active process / window title ─────────────────────────────────────
        active_frame = ctk.CTkFrame(self.monitor_frame, fg_color=BEE_COMB_MID, corner_radius=10)
        active_frame.pack(fill="x", padx=16, pady=2) 

        ctk.CTkLabel(active_frame, text="PROCESS",
                     font=ctk.CTkFont(size=10), text_color=BEE_GRAY).pack(anchor="w", padx=12, pady=(4, 0))

        self.lbl_exe_val = ctk.CTkLabel(
            active_frame, text="—",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=BEE_CREAM,
            wraplength=300, justify="left",
        )
        self.lbl_exe_val.pack(anchor="w", padx=12, pady=(0, 0)) 

        ctk.CTkLabel(active_frame, text="WINDOW TITLE",
                     font=ctk.CTkFont(size=10), text_color=BEE_GRAY).pack(anchor="w", padx=12)

        self.lbl_title_val = ctk.CTkLabel(
            active_frame, text="—",
            font=ctk.CTkFont(size=12), text_color=BEE_CREAM,
            wraplength=300, justify="left",
        )
        self.lbl_title_val.pack(anchor="w", padx=12, pady=(0, 4)) 

        # ── AI verdict ────────────────────────────────────────────────────────
        verdict_frame = ctk.CTkFrame(self.monitor_frame, fg_color=BEE_COMB_MID, corner_radius=10)
        verdict_frame.pack(fill="x", padx=16, pady=2) 

        ctk.CTkLabel(verdict_frame, text="AI VERDICT",
                     font=ctk.CTkFont(size=10), text_color=BEE_GRAY).pack(pady=(4, 0))

        self.lbl_verdict_val = ctk.CTkLabel(
            verdict_frame, text="Idle",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=BEE_GOLD,
        )
        self.lbl_verdict_val.pack(pady=(0, 2)) 

        # ── Correction button ─────────────────────────────────────────────────
        self.build_correction_button(verdict_frame)

        # ── Window switch counter ─────────────────────────────────────────────
        switches_frame = ctk.CTkFrame(self.monitor_frame, fg_color="transparent")
        switches_frame.pack(fill="x", padx=16, pady=(0, 4)) 

        ctk.CTkLabel(switches_frame, text="Window switches:",
                     font=ctk.CTkFont(size=11), text_color=BEE_GRAY).pack(side="left")

        self.lbl_switches = ctk.CTkLabel(
            switches_frame, text="0",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=BEE_CREAM,
        )
        self.lbl_switches.pack(side="left", padx=6)

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
                self.update_freq_panel()

                if self.is_paused:
                    self.monitor_frame.configure(fg_color=BEE_COMB_MID)
                    self.lbl_verdict_val.configure(text_color=BEE_GRAY)
                else:
                    self.monitor_frame.configure(fg_color=BEE_COMB_LIGHT)
                    verdict_q = next(
                        (q for q, name in QUADRANTS.items() if name in self.current_verdict), None
                    )
                    self.lbl_verdict_val.configure(text_color=Q_COLORS.get(verdict_q, BEE_GOLD))

                self.lbl_exe_val.configure(text=self.current_exe)
                self.lbl_title_val.configure(text=self.current_window)
                self.lbl_verdict_val.configure(text=self.current_verdict)

                self.graph_tick += 1
                if self.graphs_visible and self.graph_tick % 10 == 0:
                    self.refresh_graphs()

        except Exception as e:
            log_error("update_live_ui", e)
        finally:
            if self.is_tracking and self.winfo_exists():
                self.after(1000, self.update_live_ui)