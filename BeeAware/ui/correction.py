import csv
import os
from datetime import datetime

import customtkinter as ctk

import config  # imported as module so we can mutate CUSTOM_OVERRIDES, IDLE_EXES, etc. at runtime
from config import (
    BEE_AMBER, BEE_AMBER_DIM, BEE_COMB, BEE_COMB_LIGHT, BEE_COMB_MID,
    BEE_BROWN, BEE_CREAM, BEE_GRAY, BEE_RED, BEE_GREEN, BEE_GOLD,
    QUADRANTS, Q_COLORS,
)
from logger import log_error

CORRECTIONS_PATH = os.path.join(config.BASE_DIR, "data", "corrections.csv")
CORRECTIONS_COLS = [
    "timestamp",
    "exe_name",
    "window_title",
    "original_verdict",
    "corrected_label",   # 0-3, or -1 for Idle
    "corrected_quadrant", # human-readable
]


class CorrectionMixin:

    def build_correction_button(self, parent):
        """
        Call this from build_monitor_panel() after the verdict label,
        passing the verdict_frame as parent.
        Adds the 'Wrong? Fix it' button directly underneath the AI verdict.
        """
        self.btn_correction = ctk.CTkButton(
            parent,
            text="Wrong? Fix it",
            width=120, height=24,
            fg_color=BEE_COMB_MID,
            hover_color=BEE_BROWN,
            text_color=BEE_GRAY,
            font=ctk.CTkFont(size=10),
            command=self._open_correction_popup,
        )
        self.btn_correction.pack(pady=(0, 10))

    def _open_correction_popup(self):
        """
        Open a Toplevel popup showing the current exe + window title
        and buttons for the user to pick the correct quadrant or flag as idle.
        """
        if not self.is_tracking:
            return
        if self.is_paused:
            return

        exe   = self.current_exe
        title = self.current_window
        orig  = self.current_verdict

        popup = ctk.CTkToplevel(self)
        popup.title("Correct Classification")
        
        # Increased height to 440 to comfortably fit the new Idle button
        popup.geometry("420x440")
        popup.configure(fg_color=BEE_COMB)
        popup.resizable(False, False)
        popup.grab_set()   # modal

        #  Header 
        ctk.CTkLabel(
            popup, text="Correct the AI Verdict",
            font=ctk.CTkFont(size=15, weight="bold"), text_color=BEE_GOLD,
        ).pack(pady=(18, 4))

        ctk.CTkLabel(
            popup, text="─" * 44,
            text_color=BEE_BROWN, font=ctk.CTkFont(size=10),
        ).pack()

        #  Current context 
        info = ctk.CTkFrame(popup, fg_color=BEE_COMB_MID, corner_radius=8)
        info.pack(fill="x", padx=20, pady=(10, 4))

        ctk.CTkLabel(info, text="PROCESS", font=ctk.CTkFont(size=9),
                     text_color=BEE_GRAY).pack(anchor="w", padx=12, pady=(8, 0))
        ctk.CTkLabel(info, text=exe, font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=BEE_CREAM).pack(anchor="w", padx=12)

        ctk.CTkLabel(info, text="WINDOW TITLE", font=ctk.CTkFont(size=9),
                     text_color=BEE_GRAY).pack(anchor="w", padx=12, pady=(4, 0))
        ctk.CTkLabel(info, text=title[:55] + ("…" if len(title) > 55 else ""),
                     font=ctk.CTkFont(size=11), text_color=BEE_CREAM,
                     wraplength=360).pack(anchor="w", padx=12, pady=(0, 8))

        #  Current verdict
        ctk.CTkLabel(
            popup, text=f"Current verdict:  {orig}",
            font=ctk.CTkFont(size=11), text_color=BEE_GRAY,
        ).pack(pady=(4, 8))

        #  Q selection buttons 
        ctk.CTkLabel(
            popup, text="Select the correct quadrant:",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=BEE_CREAM,
        ).pack()

        btn_row = ctk.CTkFrame(popup, fg_color="transparent")
        btn_row.pack(pady=(8, 10))

        q_labels = {0: "Q1\nURGENT", 1: "Q2\nGROWTH", 2: "Q3\nNOISE", 3: "Q4\nPLAY"}

        for q in range(4):
            ctk.CTkButton(
                btn_row,
                text=q_labels[q],
                width=80, height=52,
                fg_color=Q_COLORS[q],
                hover_color=BEE_COMB_MID,
                text_color=BEE_COMB,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda chosen=q: self._apply_correction(
                    exe, title, orig, chosen, popup
                ),
            ).pack(side="left", padx=5)

        #  New System/Idle Exclusion Button 
        ctk.CTkButton(
            popup,
            text="🚫 Mark as System / Idle Process",
            width=240, height=32,
            fg_color=BEE_COMB_MID,
            hover_color=BEE_RED,
            text_color=BEE_GRAY,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self._mark_as_idle(exe, title, orig, popup),
        ).pack(pady=(10, 20))

    def _apply_correction(
        self,
        exe: str,
        title: str,
        original_verdict: str,
        corrected_label: int,
        popup,
    ):
        """
        Save correction to CSV, update CUSTOM_OVERRIDES in memory,
        and refresh the verdict label. Called when user clicks a Q button.
        """
        corrected_quadrant = QUADRANTS[corrected_label]

        #  a. Persist correction for retraining 
        self._save_correction(exe, title, original_verdict, corrected_label, corrected_quadrant)

        #  b. Update CUSTOM_OVERRIDES in memory so it sticks this session 
        override_key = exe.lower().replace(".exe", "").replace(" ", "")
        config.CUSTOM_OVERRIDES[override_key] = corrected_label
        config.CUSTOM_OVERRIDES[exe.lower()] = corrected_label
        title_key = title.lower().replace(" ", "").replace("-", "")
        config.CUSTOM_OVERRIDES[title_key] = corrected_label

        #  c. Update the live verdict label immediately 
        self.current_verdict = f"{corrected_quadrant} (Corrected)"
        self.lbl_verdict_val.configure(
            text=self.current_verdict,
            text_color=Q_COLORS[corrected_label],
        )

        popup.destroy()

    def _mark_as_idle(self, exe: str, title: str, original_verdict: str, popup):
        """
        Injects the current exe and title directly into the IDLE sets in memory.
        The watcher will instantly begin ignoring them for the rest of the session.
        """
        # Add to runtime config sets
        if exe:
            config.IDLE_EXES.add(exe.lower())
        if title:
            config.IDLE_TITLES.add(title)

        # Log to CSV with a special label (-1) so you can review exclusions later
        self._save_correction(exe, title, original_verdict, -1, "IDLE_EXCLUSION")

        # Update current UI label
        self.current_verdict = "Idle (Excluded)"
        self.lbl_verdict_val.configure(
            text=self.current_verdict,
            text_color=BEE_GRAY,
        )

        popup.destroy()

    def _save_correction(
        self,
        exe: str,
        title: str,
        original_verdict: str,
        corrected_label: int,
        corrected_quadrant: str,
    ):
        os.makedirs(os.path.dirname(CORRECTIONS_PATH), exist_ok=True)
        file_exists = os.path.isfile(CORRECTIONS_PATH)
        try:
            with open(CORRECTIONS_PATH, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(CORRECTIONS_COLS)
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    exe,
                    title,
                    original_verdict,
                    corrected_label,
                    corrected_quadrant,
                ])
        except Exception as e:
            log_error("save_correction", e)