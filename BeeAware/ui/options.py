import customtkinter as ctk

from config import BEE_AMBER, BEE_AMBER_DIM, BEE_COMB, BEE_COMB_LIGHT, BEE_CREAM


class OptionsWindow(ctk.CTkToplevel):
    def __init__(self, master, app_instance):
        super().__init__(master)

        self.app = app_instance
        self.title("Beeware Settings")
        # Allow the user to resize the options window; small displays previously
        # caused some controls to be clipped. Use a scrollable container so content
        # remains reachable at narrow heights.
        self.geometry("420x420")
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
        # Let the main window expand the scrollable region
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

        model_status = "Loaded" if getattr(self.app, "models_loaded", False) else "Not loaded"
        model_label = ctk.CTkLabel(
            container,
            text=f"Model status: {model_status}",
            text_color="white",
            anchor="w",
        )
        model_label.grid(row=4, column=0, padx=18, pady=(0, 8), sticky="w")

        # History access lives here; keep visible by stretching to available width
        self.btn_open_history = ctk.CTkButton(
            container,
            text="Open History",
            command=self.app.open_history,
            fg_color=BEE_AMBER,
            hover_color=BEE_AMBER_DIM,
        )
        self.btn_open_history.grid(row=5, column=0, padx=18, pady=(0, 12), sticky="ew")

        close_button = ctk.CTkButton(
            container,
            text="Close",
            command=self.close_window,
            fg_color=BEE_AMBER,
            hover_color="#ffbf47",
        )
        close_button.grid(row=6, column=0, padx=18, pady=(8, 18), sticky="ew")

    def toggle_notifications(self):
        self.app.notifications_enabled = self.notif_var.get() == "on"

    def toggle_strict_mode(self):
        self.app.WARNING_THRESHOLD = 900 if self.strict_var.get() == "on" else 1800

    def close_window(self):
        if hasattr(self.app, "options_window"):
            self.app.options_window = None
        self.destroy()
