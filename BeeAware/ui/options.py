import os
import json
import customtkinter as ctk
import config

from config import BEE_AMBER, BEE_AMBER_DIM, BEE_COMB, BEE_COMB_LIGHT, BEE_COMB_MID, BEE_GREEN, BEE_RED, BEE_GRAY
from notif import show_notification
from .rule_manager import RulesManagerWindow

SETTINGS_PATH = os.path.join(config.BASE_DIR, "data", "user_settings.json")

def _load_settings() -> dict:
    if os.path.isfile(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}

def _save_settings(data: dict) -> None:
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except OSError:
        pass


class OptionsWindow(ctk.CTkToplevel):
    def __init__(self, master, app_instance):
        super().__init__(master)

        self.app = app_instance
        self.title("BeeAware Settings")
        self.geometry("420x540") # Increased height slightly for status badge
        self.configure(fg_color=BEE_COMB)
        self.attributes("-topmost", True)
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self.close_window)

        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(
            self,
            text="Settings",
            font=("Segoe UI", 22, "bold"),
            text_color=BEE_AMBER,
        )
        header.grid(row=0, column=0, pady=(18, 12), padx=24, sticky="n")

        container = ctk.CTkScrollableFrame(self, fg_color=BEE_COMB_LIGHT, corner_radius=18)
        container.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- EXISTING SETTINGS GENERATION ---
        # Apply persisted settings to app state before building switches
        _saved = _load_settings()
        if "notifications_enabled" in _saved:
            self.app.notifications_enabled = _saved["notifications_enabled"]
        if "strict_mode" in _saved:
            self.app.WARNING_THRESHOLD = 900 if _saved["strict_mode"] else 1800
        if "floating_bar_enabled" in _saved:
            self.app.floating_bar_enabled = _saved["floating_bar_enabled"]
        if "camera_enabled" in _saved:
            self.app.camera_enabled = _saved["camera_enabled"]

        self.notif_var = ctk.StringVar(value="on" if self.app.notifications_enabled else "off")
        self.strict_var = ctk.StringVar(value="on" if getattr(self.app, "WARNING_THRESHOLD", 1800) == 900 else "off")

        notif_label = ctk.CTkLabel(
            container,
            text="Productivity alerts help you stay on track by keeping focus on important tasks.",
            wraplength=330,
            justify="left",
            text_color="white",
        )
        notif_label.grid(row=0, column=0, padx=18, pady=(16, 6), sticky="w")

        self.notif_switch = ctk.CTkSwitch(
            container,
            text="Enable productivity alerts",
            command=self.toggle_notifications,
            variable=self.notif_var,
            onvalue="on",
            offvalue="off",
            progress_color=BEE_AMBER,
        )
        self.notif_switch.grid(row=1, column=0, padx=18, pady=(0, 16), sticky="w")

        strict_label = ctk.CTkLabel(
            container,
            text="Strict mode makes alerts fire sooner for higher-priority items.",
            wraplength=330,
            justify="left",
            text_color="white",
        )
        strict_label.grid(row=2, column=0, padx=18, pady=(0, 6), sticky="w")

        self.strict_switch = ctk.CTkSwitch(
            container,
            text="Use strict alert timing",
            command=self.toggle_strict_mode,
            variable=self.strict_var,
            onvalue="on",
            offvalue="off",
            progress_color=BEE_AMBER,
        )
        self.strict_switch.grid(row=3, column=0, padx=18, pady=(0, 16), sticky="w")

        self.floating_bar_var = ctk.StringVar(value="on" if getattr(self.app, "floating_bar_enabled", False) else "off")
        floating_bar_label = ctk.CTkLabel(
            container,
            text="Display a floating monitor bar along the top of the screen.",
            wraplength=330,
            justify="left",
            text_color="white",
        )
        floating_bar_label.grid(row=4, column=0, padx=18, pady=(0, 6), sticky="w")

        self.floating_bar_switch = ctk.CTkSwitch(
            container,
            text="Show floating top bar",
            command=self.toggle_floating_bar,
            variable=self.floating_bar_var,
            onvalue="on",
            offvalue="off",
            progress_color=BEE_AMBER,
        )
        self.floating_bar_switch.grid(row=5, column=0, padx=18, pady=(0, 16), sticky="w")

        # --- CAMERA TRACKING SECTION WITH LIVE FEEDBACK ---
        camera_label = ctk.CTkLabel(
            container,
            text="Use your webcam to automatically detect if you are away from your PC to pause tracking.",
            wraplength=330,
            justify="left",
            text_color="white",
        )
        camera_label.grid(row=6, column=0, padx=18, pady=(0, 6), sticky="w")

        self.switch_camera = ctk.CTkSwitch(
            container,
            text="Enable Camera Presence Tracking", 
            command=self.toggle_camera,
            progress_color=BEE_AMBER,
        )
        self.switch_camera.grid(row=7, column=0, pady=(0, 4), padx=18, sticky="w")

        # THE VISUAL FEEDBACK BADGE
        self.lbl_camera_status = ctk.CTkLabel(
            container,
            text="● Camera Off",
            font=("Segoe UI", 12, "bold"),
            text_color=BEE_GRAY
        )

        self.btn_test_camera = ctk.CTkButton(
            container,
            text="Verify Camera Connection",
            command=self.test_camera_preview,
            fg_color=BEE_COMB_MID,
            hover_color=BEE_AMBER_DIM
        )
        self.btn_test_camera.grid(row=8, column=0, padx=18, pady=(0, 10), sticky="ew")

        self.lbl_camera_status.grid(row=8, column=0, padx=36, pady=(0, 16), sticky="w")
       
        if getattr(self.app, "camera_enabled", False):
            self.switch_camera.select()
        else:
            self.switch_camera.deselect()

        # Hook this open settings UI window into the live camera tracker's callback loop
        if hasattr(self.app, 'camera_tracker') and self.app.camera_tracker:
            self.app.camera_tracker.status_callback = self.update_camera_status_ui
            # Manually poll initialization state display
            if self.app.camera_tracker.is_running:
                state = "Active - User Present" if self.app.camera_tracker.user_present else "Active - User Away (Paused)"
                self.update_camera_status_ui(state)

        # --- APP BUTTONS ---
        model_status = "Loaded" if getattr(self.app, "models_ready", False) else "Not loaded"
        model_label = ctk.CTkLabel(
            container,
            text=f"Model status: {model_status}",
            text_color="white",
            anchor="w",
        )
        model_label.grid(row=9, column=0, padx=18, pady=(0, 8), sticky="w")

        self.btn_test_notif = ctk.CTkButton(
            container,
            text="Test Alert Popup",
            command=self.trigger_test_notif,
            fg_color=BEE_COMB_MID,  
            hover_color=BEE_AMBER_DIM,
            text_color="white"
        )
        self.btn_test_notif.grid(row=10, column=0, padx=18, pady=(0, 12), sticky="ew")

        self.btn_open_rules = ctk.CTkButton(
            container,
            text="Manage Rules & Exclusions",
            command=self.open_rules_manager,
            fg_color=BEE_COMB_MID,
            hover_color=BEE_AMBER_DIM,
            text_color="white"
        )
        self.btn_open_rules.grid(row=11, column=0, padx=18, pady=(0, 12), sticky="ew")

        self.btn_open_history = ctk.CTkButton(
            container,
            text="Open History",
            command=self.app.open_history if hasattr(self.app, 'open_history') else None,
            fg_color=BEE_AMBER,
            hover_color=BEE_AMBER_DIM,
        )
        self.btn_open_history.grid(row=12, column=0, padx=18, pady=(0, 12), sticky="ew")

        close_button = ctk.CTkButton(
            container,
            text="Close",
            command=self.close_window,
            fg_color=BEE_AMBER,
            hover_color="#ffbf47",
        )
        close_button.grid(row=13, column=0, padx=18, pady=(8, 18), sticky="ew")
  

    def update_camera_status_ui(self, status_text):
        """Receives live updates from the background camera thread and transforms the UI badge color."""
        if not self.winfo_exists():
            return
            
        if "User Present" in status_text:
            self.lbl_camera_status.configure(text=f"● {status_text}", text_color="#2ECC71") # Green dot
        elif "Searching" in status_text or "Initializing" in status_text:
            self.lbl_camera_status.configure(text=f"● {status_text}", text_color=BEE_AMBER) # Amber warning dot
        elif "Away" in status_text or "Unavailable" in status_text:
            self.lbl_camera_status.configure(text=f"● {status_text}", text_color="#E74C3C") # Red alert dot
        else:
            self.lbl_camera_status.configure(text=f"● {status_text}", text_color=BEE_GRAY) # Dull gray off dot

    def toggle_camera(self):
        is_on = bool(self.switch_camera.get())
        self.app.camera_enabled = is_on
        self._persist_settings()
    
        if not hasattr(self.app, 'camera_tracker') or self.app.camera_tracker is None:
            from camera import CameraPresenceTracker
            self.app.camera_tracker = CameraPresenceTracker(
                pause_callback=self.app._on_user_left,
                resume_callback=self.app._on_user_returned,
                status_callback=self.update_camera_status_ui
            )
        
  
        if is_on:
            self.app.camera_tracker.status_callback = self.update_camera_status_ui
            self.app.camera_tracker.start()
        else:
            self.app.camera_tracker.stop()
            self.update_camera_status_ui("Camera Off")
    
    def test_camera_preview(self):
        import cv2
        import threading

        # Disable button to prevent multiple windows
        self.btn_test_camera.configure(state="disabled", text="Opening...")
        self.update()

        def preview_loop():
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            
            # Check if camera actually works
            if not cap.isOpened():
                print("Camera failed to open.")
                return

            cv2.namedWindow("BeeAware Camera Preview", cv2.WINDOW_NORMAL)
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Show the feed
                cv2.imshow("BeeAware Camera Preview", frame)
                
                # Close if user hits 'q' or clicks the 'X' on the window
                if cv2.waitKey(1) & 0xFF == ord('q') or cv2.getWindowProperty("BeeAware Camera Preview", cv2.WND_PROP_VISIBLE) < 1:
                    break
            
            cap.release()
            cv2.destroyWindow("BeeAware Camera Preview")
            
            # Re-enable the button once closed
            self.btn_test_camera.configure(state="normal", text="Verify Camera Connection")

        # Run the preview in a separate thread so it doesn't freeze the Settings window
        threading.Thread(target=preview_loop, daemon=True).start()

        
    def _show_camera_popup(self, title, message, color):
        """Small inline popup for camera test results — no external dependency needed."""
        popup = ctk.CTkToplevel(self)
        popup.title(title)
        popup.geometry("320x160")
        popup.configure(fg_color=BEE_COMB)
        popup.attributes("-topmost", True)
        popup.resizable(False, False)
        popup.grab_set()

        ctk.CTkLabel(
            popup, text=title,
            font=("Segoe UI", 15, "bold"), text_color=color
        ).pack(pady=(20, 6))

        ctk.CTkLabel(
            popup, text=message,
            font=("Segoe UI", 12), text_color="white",
            wraplength=280, justify="center"
        ).pack(pady=(0, 12))

        ctk.CTkButton(
            popup, text="OK",
            command=popup.destroy,
            fg_color=color, hover_color=BEE_COMB_MID,
            width=80
        ).pack()

    def _persist_settings(self):
        """Write all toggle states to disk."""
        _save_settings({
            "notifications_enabled": self.app.notifications_enabled,
            "strict_mode": self.app.WARNING_THRESHOLD == 900,
            "floating_bar_enabled": getattr(self.app, "floating_bar_enabled", True),
            "camera_enabled": getattr(self.app, "camera_enabled", False),
        })

    def toggle_notifications(self):
        self.app.notifications_enabled = self.notif_var.get() == "on"
        self._persist_settings()

    def toggle_strict_mode(self):
        self.app.WARNING_THRESHOLD = 900 if self.strict_var.get() == "on" else 1800
        self._persist_settings()

    def toggle_floating_bar(self):
        if hasattr(self.app, 'set_floating_bar_visibility'):
            self.app.set_floating_bar_visibility(self.floating_bar_var.get() == "on")
        self._persist_settings()

    def trigger_test_notif(self):
        show_notification(
            master=self.app,
            title="Test Productivity Alert",
            message="This is a test! You've spent 45m in Q4 (Play). Time to shift focus.",
            duration=5000,
            color=BEE_AMBER
        )

    def open_rules_manager(self):
        RulesManagerWindow(self)

    def close_window(self):
        # Detach callback reference when closing window to prevent memory leaks or background thread crashing
        if hasattr(self.app, 'camera_tracker') and self.app.camera_tracker:
            self.app.camera_tracker.status_callback = None
            
        if hasattr(self.app, "options_window"):
            self.app.options_window = None
        self.destroy()