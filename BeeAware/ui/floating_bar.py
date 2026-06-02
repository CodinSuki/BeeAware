import customtkinter as ctk
from config import (
    BEE_COMB, BEE_COMB_LIGHT, BEE_COMB_MID, BEE_CREAM, BEE_GREEN,
    BEE_RED, BEE_GRAY, BEE_AMBER, BEE_AMBER_DIM, BEE_GOLD, BEE_BROWN,
)
from logger import log_error


class FloatingBar(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)

        self.app = app
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.96)

        self.screen_width = self.winfo_screenwidth()
        self.width = min(self.screen_width - 80, 1050)
        self.x_center = max(24, (self.screen_width - self.width) // 2)
        self.y_offset = 12
        self.hidden_height = 4
        self.visible_height = 80
        self.is_expanded = False
        self.hide_job = None

        self.geometry(f"{self.width}x{self.hidden_height}+{self.x_center}+{self.y_offset}")
        self.configure(fg_color=BEE_COMB)
        self.attributes("-alpha", 0.01)
        self.lift()

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        self._build_contents()
        self._collapse()
        self.after(200, self._schedule_refresh)

    def _build_contents(self):
        self.container = ctk.CTkFrame(
            self,
            fg_color=BEE_COMB_LIGHT,
            corner_radius=18,
            border_width=1,
            border_color=BEE_COMB,
        )
        self.container.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.handle = ctk.CTkFrame(
            self.container,
            fg_color=BEE_COMB_MID,
            corner_radius=8,
            width=140,
            height=4,
        )
        self.handle.place(relx=0.5, y=10, anchor="n")

        self.lbl_title = ctk.CTkLabel(
            self.container,
            text="BeeAware Live Monitor",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=BEE_CREAM,
        )
        self.lbl_title.place(relx=0.05, y=26, anchor="w")

        self.lbl_status = ctk.CTkLabel(
            self.container,
            text="● Idle",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=BEE_GRAY,
        )
        self.lbl_status.place(relx=0.05, y=46, anchor="w")

        self.lbl_live = ctk.CTkLabel(
            self.container,
            text="Focus 00:00  |  Distracted 00:00",
            font=ctk.CTkFont(size=12),
            text_color=BEE_CREAM,
        )
        self.lbl_live.place(relx=0.5, y=40, anchor="center")

        # --- UPDATED VERDICT LABEL PLACEMENT ---
        self.lbl_verdict = ctk.CTkLabel(
            self.container,
            text="Verdict: Idle",
            font=ctk.CTkFont(size=12),
            text_color=BEE_GRAY,
        )
        # Anchored East so long strings expand to the left
        self.lbl_verdict.place(relx=0.48, y=58, anchor="e")

        # --- NEW FIX BUTTON ---
        self.btn_fix = ctk.CTkButton(
            self.container,
            text="✎ Fix",
            width=45, height=20,
            fg_color=BEE_COMB_MID,
            hover_color=BEE_BROWN,
            text_color=BEE_CREAM,
            font=ctk.CTkFont(size=10),
            command=self._on_fix,
        )
        # Anchored West so it stays safely to the right of the verdict text
        self.btn_fix.place(relx=0.52, y=58, anchor="w")

        self.btn_pause = ctk.CTkButton(
            self.container,
            text="Pause",
            width=100,
            fg_color=BEE_AMBER,
            hover_color=BEE_AMBER_DIM,
            command=self._on_pause,
        )
        self.btn_pause.place(relx=0.78, y=42, anchor="e")

        self.btn_end = ctk.CTkButton(
            self.container,
            text="End",
            width=100,
            fg_color=BEE_RED,
            hover_color="#8f3f30",
            command=self._on_end,
        )
        self.btn_end.place(relx=0.96, y=42, anchor="e")

        self.container.bind("<Enter>", self._on_enter)
        self.container.bind("<Leave>", self._on_leave)
        
        # Ensure btn_fix is included here so hovering it keeps the bar open
        for widget in (
            self.handle,
            self.lbl_title,
            self.lbl_status,
            self.lbl_live,
            self.lbl_verdict,
            self.btn_pause,
            self.btn_end,
            self.btn_fix, 
        ):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, event=None):
        if self.hide_job:
            self.after_cancel(self.hide_job)
            self.hide_job = None
        self._expand()

    def _on_leave(self, event=None):
        if self.hide_job:
            self.after_cancel(self.hide_job)
        self.hide_job = self.after(300, self._collapse)

    def _expand(self):
        if not self.is_expanded:
            self.is_expanded = True
            self.attributes("-alpha", 0.96)
            self.geometry(f"{self.width}x{self.visible_height}+{self.x_center}+{self.y_offset}")

    def _collapse(self):
        if self.is_expanded:
            self.is_expanded = False
        self.attributes("-alpha", 0.01)
        self.geometry(f"{self.width}x{self.hidden_height}+{self.x_center}+{self.y_offset}")

    # --- NEW METHOD TO TRIGGER THE POPUP ---
    def _on_fix(self):
        try:
            self.app._open_correction_popup()
        except Exception as e:
            log_error("floating_bar_fix", e)

    def _on_pause(self):
        try:
            self.app.toggle_pause()
        except Exception as e:
            log_error("floating_bar_pause", e)

    def _on_end(self):
        try:
            self.app.exit_app()
        except Exception as e:
            log_error("floating_bar_end", e)

    def _schedule_refresh(self):
        try:
            prod = self.app.live_stats[0] + self.app.live_stats[1]
            dist = self.app.live_stats[2] + self.app.live_stats[3]
            self.lbl_live.configure(
                text=f"Focus {self.app.format_time(prod)}  |  Distracted {self.app.format_time(dist)}"
            )

            verdict = self.app.current_verdict or "Idle"
            color = BEE_GOLD
            if "IDLE" in verdict.upper():
                color = BEE_GRAY
            elif "PAUSED" in verdict.upper():
                color = BEE_AMBER
            elif "NOISE" in verdict.upper():
                color = BEE_RED

            self.lbl_status.configure(text=f"● {self.app.lbl_status.cget('text')}", text_color=self.app.lbl_status.cget('text_color'))
            self.lbl_verdict.configure(text=f"Verdict: {verdict}", text_color=color)

            if self.app.is_paused:
                self.btn_pause.configure(text="Resume")
            else:
                self.btn_pause.configure(text="Pause")
        except Exception as e:
            log_error("floating_bar_refresh", e)
        finally:
            self.after(400, self._schedule_refresh)