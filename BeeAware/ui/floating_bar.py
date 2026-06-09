import customtkinter as ctk
from PIL import Image
import cv2
import threading

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
        
        self.feed_active = False
        self.latest_frame = None
        self.camera_lock = threading.Lock()

        # Initial collapsed state
        self.geometry(f"{self.width}x{self.hidden_height}+{self.x_center}+{self.y_offset}")
        self.configure(fg_color=BEE_COMB)
        self.attributes("-alpha", 0.01)
        
        self._build_contents()
        self.after(200, self._schedule_refresh)

    def _build_contents(self):
        # Base container
        self.container = ctk.CTkFrame(self, fg_color=BEE_COMB_LIGHT, corner_radius=18, border_width=1, border_color=BEE_COMB)
        self.container.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Build UI Elements
        self.handle = ctk.CTkFrame(self.container, fg_color=BEE_COMB_MID, corner_radius=8, width=140, height=4)
        self.handle.place(relx=0.5, y=10, anchor="n")
        
        self.lbl_title = ctk.CTkLabel(self.container, text="BeeAware Live Monitor", font=ctk.CTkFont(size=14, weight="bold"), text_color=BEE_CREAM)
        self.lbl_title.place(relx=0.05, y=26, anchor="w")
        
        self.lbl_status = ctk.CTkLabel(self.container, text="● Idle", font=ctk.CTkFont(size=12, weight="bold"), text_color=BEE_GRAY)
        self.lbl_status.place(relx=0.05, y=46, anchor="w")

        self.lbl_live = ctk.CTkLabel(self.container, text="Focus 00:00 | Distracted 00:00", font=ctk.CTkFont(size=12), text_color=BEE_CREAM)
        self.lbl_live.place(relx=0.45, y=26, anchor="center")
        
        self.lbl_verdict = ctk.CTkLabel(self.container, text="Verdict: Idle", font=ctk.CTkFont(size=12), text_color=BEE_GRAY)
        self.lbl_verdict.place(relx=0.35, y=50, anchor="w")

        self.btn_fix = ctk.CTkButton(self.container, text="✎ Fix", width=50, height=20, fg_color=BEE_COMB_MID, command=self._on_fix)
        self.btn_fix.place(relx=0.55, y=50, anchor="w")

        self.btn_preview = ctk.CTkButton(self.container, text="👁 Preview", width=70, height=20, fg_color=BEE_COMB_MID, command=self._toggle_preview)
        self.btn_preview.place(relx=0.65, y=50, anchor="w")

        self.btn_pause = ctk.CTkButton(self.container, text="Pause", width=80, height=25, fg_color=BEE_AMBER, command=self._on_pause)
        self.btn_pause.place(relx=0.82, y=40, anchor="center")

        self.btn_end = ctk.CTkButton(self.container, text="End", width=80, height=25, fg_color=BEE_RED, command=self._on_end)
        self.btn_end.place(relx=0.93, y=40, anchor="center")

        self.lbl_video_feed = ctk.CTkLabel(self.container, text="", width=320, height=240, fg_color="black")
        self.lbl_video_feed.place(relx=0.5, y=90, anchor="n")

        # --- THE FIX: BIND EVERY WIDGET ---
        all_widgets = [
            self.container, self.handle, self.lbl_title, self.lbl_status, 
            self.lbl_live, self.lbl_verdict, self.btn_fix, self.btn_preview, 
            self.btn_pause, self.btn_end, self.lbl_video_feed
        ]
        for widget in all_widgets:
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, event=None):
        if self.hide_job:
            self.after_cancel(self.hide_job)
            self.hide_job = None
        self._expand()

    def _on_leave(self, event=None):
        # Only collapse if the mouse really left the window
        x, y = self.winfo_pointerxy()
        if self.winfo_containing(x, y) != self.container:
            self.hide_job = self.after(500, self._collapse)

    def _expand(self):
        if not self.is_expanded:
            self.is_expanded = True
            self.attributes("-alpha", 0.50)
            h = 340 if self.feed_active else 80
            self.geometry(f"{self.width}x{h}+{self.x_center}+{self.y_offset}")

    def _collapse(self):
        self.is_expanded = False
        self.attributes("-alpha", 0.01)
        self.geometry(f"{self.width}x{self.hidden_height}+{self.x_center}+{self.y_offset}")

    def _toggle_preview(self):
        # Gate: preview requires camera to be enabled in settings
        if not getattr(self.app, "camera_enabled", False):
            self._show_camera_off_popup()
            return

        self.feed_active = not self.feed_active
        if self.feed_active:
            self.btn_preview.configure(text="■ Stop")
            threading.Thread(target=self._camera_worker, daemon=True).start()
            self._update_ui_image()
        else:
            self.btn_preview.configure(text="👁 Preview")
            self.lbl_video_feed.configure(image=None)
        self._expand()

    def _show_camera_off_popup(self):
        """Inform the user that camera tracking is disabled in settings."""
        popup = ctk.CTkToplevel(self)
        popup.title("Camera Disabled")
        popup.geometry("300x140")
        popup.configure(fg_color=BEE_COMB)
        popup.attributes("-topmost", True)
        popup.resizable(False, False)
        popup.grab_set()

        ctk.CTkLabel(
            popup, text="Camera is turned off",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=BEE_AMBER,
        ).pack(pady=(20, 6))

        ctk.CTkLabel(
            popup, text="Enable Camera Presence Tracking\nin Settings to use this feature.",
            font=ctk.CTkFont(size=11), text_color=BEE_GRAY,
            justify="center",
        ).pack(pady=(0, 12))

        ctk.CTkButton(
            popup, text="OK", width=80,
            fg_color=BEE_AMBER, hover_color=BEE_COMB_MID,
            command=popup.destroy,
        ).pack()

    def _camera_worker(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        while self.feed_active:
            ret, frame = cap.read()
            if ret:
                with self.camera_lock:
                    self.latest_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        cap.release()

    def _update_ui_image(self):
        if not self.feed_active: return
        with self.camera_lock:
            if self.latest_frame is not None:
                img = Image.fromarray(self.latest_frame)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(320, 240))
                self.lbl_video_feed.configure(image=ctk_img)
                self.lbl_video_feed.image = ctk_img
        self.after(100, self._update_ui_image)

    def _schedule_refresh(self):
        """Pull live state from the watcher and update all floating bar labels."""
        try:
            app = self.app

            # --- Status dot + text ---
            if app.is_paused:
                self.lbl_status.configure(text="● Paused", text_color=BEE_AMBER)
            elif getattr(app, "camera_auto_paused", False):
                self.lbl_status.configure(text="● Away", text_color=BEE_AMBER_DIM)
            elif app.is_tracking:
                self.lbl_status.configure(text="● Watching", text_color=BEE_GREEN)
            else:
                self.lbl_status.configure(text="● Idle", text_color=BEE_GRAY)

            # --- Focus / Distracted time ---
            productive = app.live_stats[0] + app.live_stats[1]
            distracted = app.live_stats[2] + app.live_stats[3]
            self.lbl_live.configure(
                text=f"Focus {app.format_time(productive)} | Distracted {app.format_time(distracted)}"
            )

            # --- Current verdict ---
            verdict = app.current_verdict or "Idle"
            # Pick a colour that matches the quadrant
            from config import QUADRANTS, Q_COLORS
            verdict_color = BEE_GRAY
            for q, name in QUADRANTS.items():
                if name in verdict:
                    verdict_color = Q_COLORS[q]
                    break
            self.lbl_verdict.configure(text=f"Verdict: {verdict}", text_color=verdict_color)

            # --- Pause button label mirrors app state ---
            if app.is_paused:
                self.btn_pause.configure(text="Resume", fg_color=BEE_AMBER_DIM)
            else:
                self.btn_pause.configure(text="Pause", fg_color=BEE_AMBER)

        except Exception as e:
            log_error("floating_bar_refresh", e)

        self.after(400, self._schedule_refresh)

    def _on_fix(self): self.app._open_correction_popup()
    def _on_pause(self): self.app.toggle_pause()
    def _on_end(self): self.app.exit_app()