# options.py — Settings menu for Beeware

import customtkinter as ctk
from config import BEE_COMB, BEE_COMB_LIGHT, BEE_AMBER

class OptionsWindow(ctk.CTkToplevel):
    def __init__(self, master, app_instance):
        super().__init__(master)
        
        self.title("Beeware Options")
        self.geometry("350x250")
        self.configure(fg_color=BEE_COMB)
        self.attributes("-topmost", True) # Keeps settings above the main app
        
        # Store a reference to the main app so we can change its variables
        self.app = app_instance 

        # Title
        self.lbl_title = ctk.CTkLabel(self, text="Settings", font=("Segoe UI", 18, "bold"), text_color=BEE_AMBER)
        self.lbl_title.pack(pady=(15, 15))

        # --- TOGGLE 1: Notifications ---
        # We check the app's current state to set the switch's initial position
        notif_initial = ctk.StringVar(value="on" if self.app.notifications_enabled else "off")
        self.switch_notif = ctk.CTkSwitch(
            self, 
            text="Enable Productivity Alerts",
            command=self.toggle_notifs,
            variable=notif_initial,
            onvalue="on",
            offvalue="off",
            progress_color=BEE_AMBER
        )
        self.switch_notif.pack(pady=10, padx=20, anchor="w")

        # --- TOGGLE 2: Strict Mode ---
        strict_initial = ctk.StringVar(value="on" if self.app.WARNING_THRESHOLD == 900 else "off")
        self.switch_strict = ctk.CTkSwitch(
            self, 
            text="Strict Mode (15m Alerts)",
            command=self.toggle_strict_mode,
            variable=strict_initial,
            onvalue="on",
            offvalue="off",
            progress_color=BEE_AMBER
        )
        self.switch_strict.pack(pady=10, padx=20, anchor="w")

    # --- Methods to handle the switch clicks ---
    def toggle_notifs(self):
        # Update the main app's variable based on the switch state
        if self.switch_notif.get() == "on":
            self.app.notifications_enabled = True
        else:
            self.app.notifications_enabled = False

    def toggle_strict_mode(self):
        # Changes the warning threshold in app.py directly
        if self.switch_strict.get() == "on":
            self.app.WARNING_THRESHOLD = 900  # 15 minutes
        else:
            self.app.WARNING_THRESHOLD = 1800 # 30 minutes