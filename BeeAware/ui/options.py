import customtkinter as ctk
import config  # Imported as a module so we can mutate the global sets/dicts

from config import BEE_AMBER, BEE_AMBER_DIM, BEE_COMB, BEE_COMB_LIGHT, BEE_COMB_MID, BEE_CREAM, BEE_RED, BEE_GRAY
from notif import show_notification
from .rule_manager import RulesManagerWindow


class OptionsWindow(ctk.CTkToplevel):
    def __init__(self, master, app_instance):
        super().__init__(master)

        self.app = app_instance
        self.title("BeeAware Settings")
        
        # Increased height to 510 to fit the new button
        self.geometry("420x510") 
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

        # Use a scrollable frame so the options are accessible on low-resolution screens
        container = ctk.CTkScrollableFrame(self, fg_color=BEE_COMB_LIGHT, corner_radius=18)
        container.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

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

        model_status = "Loaded" if getattr(self.app, "models_ready", False) else "Not loaded"
        model_label = ctk.CTkLabel(
            container,
            text=f"Model status: {model_status}",
            text_color="white",
            anchor="w",
        )
        model_label.grid(row=6, column=0, padx=18, pady=(0, 8), sticky="w")

        self.btn_test_notif = ctk.CTkButton(
            container,
            text="Test Alert Popup",
            command=self.trigger_test_notif,
            fg_color=BEE_COMB_MID,  
            hover_color=BEE_AMBER_DIM,
            text_color="white"
        )
        self.btn_test_notif.grid(row=7, column=0, padx=18, pady=(0, 12), sticky="ew")

        # --- RULES MANAGER BUTTON ---
        self.btn_open_rules = ctk.CTkButton(
            container,
            text="Manage Rules & Exclusions",
            command=self.open_rules_manager,
            fg_color=BEE_COMB_MID,
            hover_color=BEE_AMBER_DIM,
            text_color="white"
        )
        self.btn_open_rules.grid(row=8, column=0, padx=18, pady=(0, 12), sticky="ew")

        self.btn_open_history = ctk.CTkButton(
            container,
            text="Open History",
            command=self.app.open_history if hasattr(self.app, 'open_history') else None,
            fg_color=BEE_AMBER,
            hover_color=BEE_AMBER_DIM,
        )
        self.btn_open_history.grid(row=9, column=0, padx=18, pady=(0, 12), sticky="ew")

        close_button = ctk.CTkButton(
            container,
            text="Close",
            command=self.close_window,
            fg_color=BEE_AMBER,
            hover_color="#ffbf47",
        )
        close_button.grid(row=10, column=0, padx=18, pady=(8, 18), sticky="ew")

    def toggle_notifications(self):
        self.app.notifications_enabled = self.notif_var.get() == "on"

    def toggle_strict_mode(self):
        self.app.WARNING_THRESHOLD = 900 if self.strict_var.get() == "on" else 1800

    def toggle_floating_bar(self):
        if hasattr(self.app, 'set_floating_bar_visibility'):
            self.app.set_floating_bar_visibility(self.floating_bar_var.get() == "on")

    def trigger_test_notif(self):
        show_notification(
            master=self.app,
            title="Test Productivity Alert",
            message="This is a test! You've spent 45m in Q4 (Play). Time to shift focus.",
            duration=5000,
            color=BEE_AMBER
        )

    # --- HOOK TO OPEN THE NEW MANAGER ---
    def open_rules_manager(self):
        RulesManagerWindow(self)

    def close_window(self):
        if hasattr(self.app, "options_window"):
            self.app.options_window = None
        self.destroy()