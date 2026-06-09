import csv
import os
import json
from datetime import datetime

import customtkinter as ctk

import config
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
    "corrected_label",
    "corrected_quadrant",
]


# ---------------------------------------------------------------------------
# Module-level helpers — imported by app.py to guarantee save & lookup
# always use identical key normalisation.
# ---------------------------------------------------------------------------

def normalize_exe_key(exe: str) -> str:
    """'Chrome.exe' -> 'chrome'  |  single source of truth for exe keys."""
    return exe.lower().replace(".exe", "").strip()


def normalize_title_key(title: str) -> str:
    """Lowercase + strip only — keeps spaces so titles stay matchable."""
    return title.lower().strip()


class CorrectionMixin:

    # Aliases so existing code calling self._normalize_*() still works
    _normalize_exe_key   = staticmethod(normalize_exe_key)
    _normalize_title_key = staticmethod(normalize_title_key)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def build_correction_button(self, parent):
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
        if not self.is_tracking:
            return
        if self.is_paused:
            return

        exe   = self.current_exe
        title = self.current_window
        orig  = self.current_verdict

        popup = ctk.CTkToplevel(self)
        popup.title("Correct Classification")
        popup.geometry("420x440")
        popup.configure(fg_color=BEE_COMB)
        popup.resizable(False, False)
        popup.grab_set()

        ctk.CTkLabel(
            popup, text="Correct the AI Verdict",
            font=ctk.CTkFont(size=15, weight="bold"), text_color=BEE_GOLD,
        ).pack(pady=(18, 4))

        ctk.CTkLabel(
            popup, text="─" * 44,
            text_color=BEE_BROWN, font=ctk.CTkFont(size=10),
        ).pack()

        info = ctk.CTkFrame(popup, fg_color=BEE_COMB_MID, corner_radius=8)
        info.pack(fill="x", padx=20, pady=(10, 4))

        ctk.CTkLabel(
            info, text="PROCESS",
            font=ctk.CTkFont(size=9), text_color=BEE_GRAY,
        ).pack(anchor="w", padx=12, pady=(8, 0))
        ctk.CTkLabel(
            info, text=exe,
            font=ctk.CTkFont(size=12, weight="bold"), text_color=BEE_CREAM,
        ).pack(anchor="w", padx=12)

        ctk.CTkLabel(
            info, text="WINDOW TITLE",
            font=ctk.CTkFont(size=9), text_color=BEE_GRAY,
        ).pack(anchor="w", padx=12, pady=(4, 0))
        ctk.CTkLabel(
            info,
            text=title[:55] + ("…" if len(title) > 55 else ""),
            font=ctk.CTkFont(size=11), text_color=BEE_CREAM, wraplength=360,
        ).pack(anchor="w", padx=12, pady=(0, 8))

        ctk.CTkLabel(
            popup,
            text=f"Current verdict:  {orig}",
            font=ctk.CTkFont(size=11), text_color=BEE_GRAY,
        ).pack(pady=(4, 8))
        ctk.CTkLabel(
            popup, text="Select the correct quadrant:",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=BEE_CREAM,
        ).pack()

        btn_row = ctk.CTkFrame(popup, fg_color="transparent")
        btn_row.pack(pady=(8, 10))

        q_labels = {0: "Q1\nURGENT", 1: "Q2\nGROWTH", 2: "Q3\nNOISE", 3: "Q4\nPLAY"}
        for q in range(4):
            ctk.CTkButton(
                btn_row, text=q_labels[q], width=80, height=52,
                fg_color=Q_COLORS[q], hover_color=BEE_COMB_MID, text_color=BEE_COMB,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda chosen=q: self._apply_correction(exe, title, orig, chosen, popup),
            ).pack(side="left", padx=5)

        ctk.CTkButton(
            popup, text="🚫 Mark as System / Idle Process", width=240, height=32,
            fg_color=BEE_COMB_MID, hover_color=BEE_RED, text_color=BEE_GRAY,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self._mark_as_idle(exe, title, orig, popup),
        ).pack(pady=(10, 20))

    # ------------------------------------------------------------------
    # Correction logic
    # ------------------------------------------------------------------

    def _apply_correction(self, exe, title, original_verdict, corrected_label, popup):
        corrected_quadrant = config.QUADRANTS[corrected_label]

        # 1. Append to CSV audit log
        self._save_correction(exe, title, original_verdict, corrected_label, corrected_quadrant)

        # 2. Persist override by exe (primary key — stable across title changes)
        exe_key = self._normalize_exe_key(exe)
        self._save_to_json(exe_key, corrected_label)

        # 3. Also persist by title only when it's specific enough to be useful
        if title and len(title.strip()) > 5:
            title_key = self._normalize_title_key(title)
            self._save_to_json(title_key, corrected_label)

        # 4. Refresh UI
        self.current_verdict = f"{corrected_quadrant} (Corrected)"
        self.lbl_verdict_val.configure(
            text=self.current_verdict,
            text_color=config.Q_COLORS[corrected_label],
        )
        popup.destroy()

    def _save_to_json(self, key: str, value: int) -> None:
        """
        Write a single override key→value to disk.

        Always reads the current file first so we never clobber other keys
        that were written since the app started.
        """
        full_path = os.path.abspath(config.OVERRIDES_JSON_PATH)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # --- read what's already on disk ---
        current: dict = {}
        if os.path.isfile(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    current = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                log_error("load_overrides_for_update", e)
                current = {}

        # --- merge and write ---
        current[key] = value
        config.CUSTOM_OVERRIDES[key] = value   # keep in-memory dict in sync

        try:
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=4)
        except OSError as e:
            log_error("save_to_json", e)

    def _mark_as_idle(self, exe: str, title: str, original_verdict: str, popup):
        if exe:
            config.IDLE_EXES.add(exe.lower())
        if title:
            config.IDLE_TITLES.add(title)

        self._save_correction(exe, title, original_verdict, -1, "IDLE_EXCLUSION")
        self._persist_idle_exclusions()

        self.current_verdict = "Idle (Excluded)"
        self.lbl_verdict_val.configure(text=self.current_verdict, text_color=BEE_GRAY)
        popup.destroy()

    def _persist_idle_exclusions(self) -> None:
        """Write IDLE_EXES and IDLE_TITLES to disk so they survive restarts."""
        full_path = os.path.abspath(config.IDLE_EXCLUSIONS_PATH)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        payload = {
            "idle_exes":   sorted(config.IDLE_EXES),
            "idle_titles": sorted(config.IDLE_TITLES),
        }
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4)
        except OSError as e:
            log_error("persist_idle_exclusions", e)

    def _save_correction(
        self,
        exe: str,
        title: str,
        original_verdict: str,
        corrected_label: int,
        corrected_quadrant: str,
    ) -> None:
        """Append one row to the CSV audit log."""
        os.makedirs(os.path.dirname(CORRECTIONS_PATH), exist_ok=True)
        file_exists = os.path.isfile(CORRECTIONS_PATH)
        try:
            with open(CORRECTIONS_PATH, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(CORRECTIONS_COLS)
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    exe, title, original_verdict, corrected_label, corrected_quadrant,
                ])
        except Exception as e:
            log_error("save_correction", e)