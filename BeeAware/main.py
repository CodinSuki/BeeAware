# main.py — entry point for BeeAware
# Run this file to start the application.

import customtkinter as ctk
from app import BeeAwareApp

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

if __name__ == "__main__":
    app = BeeAwareApp()
    app.mainloop()
    try:
        app.destroy()
    except Exception:
        pass
