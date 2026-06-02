# notif.py — custom notification popup for BeeAware

import customtkinter as ctk
import ctypes
from config import BEE_COMB, BEE_COMB_LIGHT, BEE_CREAM, BEE_AMBER

class BeeNotification(ctk.CTkToplevel):
    def __init__(self, master=None, title="BeeAware", message="", duration=4000, color=BEE_AMBER):
        """
        A custom, borderless popup notification.
        :param duration: Time in milliseconds before the popup auto-closes.
        :param color: The accent color for the title and border.
        """
        super().__init__(master)
        
        self.title(title)
        
        # Remove standard OS window decorations
        self.overrideredirect(True)
        # Keep the notification always on top of other windows
        self.attributes("-topmost", True)

   # Forces Windows to display the UI without stealing keyboard/mouse focus
        try:
            self.update_idletasks() # Ensure the window is drawn in memory first
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            
            # Grab current window styles and append the NOACTIVATE flag
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE)
        except Exception:
            pass # Failsafe in case of rendering quirks, keeps the app running
        
        
        self.configure(fg_color=BEE_COMB)
        
        # Geometry setup (Bottom Right Corner)
        width = 320
        height = 100
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Calculate position (offset from bottom right)
        x = screen_width - width - 20
        y = screen_height - height - 60 
        
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Main Frame for styling
        self.frame = ctk.CTkFrame(
            self, 
            fg_color=BEE_COMB_LIGHT, 
            corner_radius=8, 
            border_width=2, 
            border_color=color
        )
        self.frame.pack(expand=True, fill="both", padx=4, pady=4)
        
        # Title Label
        self.lbl_title = ctk.CTkLabel(
            self.frame, 
            text=title, 
            font=("Segoe UI", 14, "bold"), 
            text_color=color
        )
        self.lbl_title.pack(pady=(10, 2), padx=15, anchor="w")
        
        # Message Label
        self.lbl_msg = ctk.CTkLabel(
            self.frame, 
            text=message, 
            font=("Segoe UI", 12), 
            text_color=BEE_CREAM, 
            wraplength=280, 
            justify="left"
        )
        self.lbl_msg.pack(pady=(0, 10), padx=15, anchor="nw")
        
        # Bind click events to allow the user to dismiss it early
        self.frame.bind("<Button-1>", self.dismiss)
        self.lbl_title.bind("<Button-1>", self.dismiss)
        self.lbl_msg.bind("<Button-1>", self.dismiss)
        
        # Auto-destroy after the specified duration
        self.after(duration, self.dismiss)

    def dismiss(self, event=None):
        self.destroy()

def show_notification(master=None, title="BeeAware", message="", duration=4000, color=BEE_AMBER):
    """
    Helper function to easily trigger a notification from anywhere in the app.
    """
    BeeNotification(master=master, title=title, message=message, duration=duration, color=color)    