# main.py — entry point for Beeware
# Run this file to start the application.

import customtkinter as ctk
from app import BeewareApp

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

if __name__ == "__main__":
    app = BeewareApp()
    app.mainloop()
    try:
        app.destroy()
    except Exception:
        pass
