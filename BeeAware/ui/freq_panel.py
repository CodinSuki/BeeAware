# ui/freq_panel.py

import os
import ctypes
from ctypes import wintypes
import win32gui
import win32api
import win32con
import customtkinter as ctk
import tkinter as tk
from PIL import Image
from config import (
    BEE_GOLD, BEE_COMB_LIGHT, BEE_COMB_MID, BEE_GRAY,
    BEE_CREAM, BEE_COMB, Q_COLORS
)

class FreqPanelMixin:
    def build_freq_panel(self):
        """Builds the Top App Performance panel (Column 1 of the Insight Row)."""
        self.icon_cache = {} # Cache CTkImage objects to prevent flicker
        self.freq_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=BEE_COMB_LIGHT)
        self.freq_frame.grid(row=2, column=1, sticky="nsew", padx=(10, 20), pady=(0, 20))
        
        self.freq_frame.grid_columnconfigure(0, weight=1)
        self.freq_frame.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self.freq_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            header, text="📊 TOP APP PERFORMANCE",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=BEE_GOLD,
        ).pack(side="left")

        # Container for the app rows
        self.apps_list_frame = ctk.CTkFrame(self.freq_frame, fg_color=BEE_COMB_MID, corner_radius=8)
        self.apps_list_frame.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.apps_list_frame.grid_columnconfigure(0, weight=1)
        self.apps_list_frame.grid_rowconfigure(0, weight=1)

        self.apps_list_canvas = tk.Canvas(
            self.apps_list_frame,
            bg=BEE_COMB_MID,
            highlightthickness=0,
        )
        self.apps_list_canvas.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)

        self.apps_list_scrollbar = ctk.CTkScrollbar(
            self.apps_list_frame,
            orientation="vertical",
            command=self.apps_list_canvas.yview,
        )
        self.apps_list_scrollbar.grid(row=0, column=1, sticky="ns", padx=(6, 10), pady=8)

        self.apps_list_canvas.configure(yscrollcommand=self.apps_list_scrollbar.set)

        self.apps_rows_container = ctk.CTkFrame(self.apps_list_canvas, fg_color="transparent")
        self.app_rows_window = self.apps_list_canvas.create_window(
            (0, 0), window=self.apps_rows_container, anchor="nw"
        )

        self.apps_rows_container.bind(
            "<Configure>",
            lambda event: self.apps_list_canvas.configure(scrollregion=self.apps_list_canvas.bbox("all")),
        )
        self.apps_list_canvas.bind(
            "<Configure>",
            lambda event: self.apps_list_canvas.itemconfig(self.app_rows_window, width=event.width),
        )

        # Pre-create 5 slots for Top Apps
        self.app_rows = []
        for i in range(5):
            row_f = ctk.CTkFrame(self.apps_rows_container, fg_color="transparent")
            row_f.grid(row=i, column=0, sticky="ew", padx=10, pady=4)
            row_f.grid_columnconfigure(2, weight=1)

            icon_lbl = ctk.CTkLabel(
                row_f,
                text="📦",
                width=24,
                height=24,
                fg_color="transparent",
            )
            icon_lbl.pack(side="left", padx=(0, 8))

            q_badge = ctk.CTkLabel(
                row_f,
                text="--",
                width=35,
                height=20,
                corner_radius=4,
                fg_color=BEE_GRAY,
                text_color=BEE_COMB,
                font=("Segoe UI", 10, "bold"),
            )
            q_badge.pack(side="left", padx=(0, 10))

            name_lbl = ctk.CTkLabel(
                row_f,
                text="Awaiting data...",
                font=("Segoe UI", 11),
                text_color=BEE_CREAM,
            )
            name_lbl.pack(side="left", fill="both", expand=True)

            time_lbl = ctk.CTkLabel(
                row_f,
                text="00m 00s",
                font=("Segoe UI", 10),
                text_color=BEE_GRAY,
            )
            time_lbl.pack(side="right", padx=(10, 0))

            self.app_rows.append(
                {"frame": row_f, "icon": icon_lbl, "badge": q_badge, "name": name_lbl, "time": time_lbl}
            )

    def _get_app_icon(self, exe_path):
        """Extract icon from EXE path and return a CTkImage."""
        print(f"_get_app_icon: exe_path={exe_path!r}")
        if not exe_path or not os.path.exists(exe_path):
            print("  icon path missing or does not exist")
            return None

        if exe_path in self.icon_cache:
            print("  icon from cache")
            return self.icon_cache[exe_path]

        try:
            icons = win32gui.ExtractIconEx(exe_path, 0)[1]
            if not icons:
                raise RuntimeError("no icon handles returned")

            hicon = icons[0]
            icon_size = (16, 16)

            hdc = win32gui.GetDC(0)
            hdc_mem = win32gui.CreateCompatibleDC(hdc)
            hbmp = win32gui.CreateCompatibleBitmap(hdc, icon_size[0], icon_size[1])
            old_obj = win32gui.SelectObject(hdc_mem, hbmp)
            win32gui.DrawIconEx(hdc_mem, 0, 0, hicon, icon_size[0], icon_size[1], 0, 0, win32con.DI_NORMAL)
            win32gui.SelectObject(hdc_mem, old_obj)

            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", wintypes.DWORD),
                    ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD),
                    ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG),
                    ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD),
                ]

            class BITMAPINFO(ctypes.Structure):
                _fields_ = [
                    ("bmiHeader", BITMAPINFOHEADER),
                    ("bmiColors", wintypes.DWORD * 3),
                ]

            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = icon_size[0]
            bmi.bmiHeader.biHeight = -icon_size[1]   # top-down DIB
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = win32con.BI_RGB
            bmi.bmiHeader.biSizeImage = 0

            buffer_size = icon_size[0] * icon_size[1] * 4
            buffer = ctypes.create_string_buffer(buffer_size)

            gdi32 = ctypes.windll.gdi32
            gdi32.GetDIBits.argtypes = [
                ctypes.c_void_p,
                ctypes.c_void_p,
                wintypes.UINT,
                wintypes.UINT,
                ctypes.c_void_p,
                ctypes.POINTER(BITMAPINFO),
                wintypes.UINT,
            ]
            gdi32.GetDIBits.restype = wintypes.INT

            result = gdi32.GetDIBits(
                ctypes.c_void_p(int(hdc_mem)),
                ctypes.c_void_p(int(hbmp)),
                0,
                icon_size[1],
                buffer,
                ctypes.byref(bmi),
                win32con.DIB_RGB_COLORS,
            )
            if result == 0:
                raise RuntimeError("GetDIBits failed")

            raw_bytes = bytes(buffer)
            img = Image.frombytes("RGBA", icon_size, raw_bytes, "raw", "BGRA")
            img = img.convert("RGBA")

            ctk_image = ctk.CTkImage(light_image=img, size=icon_size)
            self.icon_cache[exe_path] = ctk_image
            print("  icon created successfully")
            return ctk_image

        except Exception as e:
            print("  icon load failed:", e)
            return None

        finally:
            if "hicon" in locals():
                win32gui.DestroyIcon(hicon)
            if "hbmp" in locals():
                win32gui.DeleteObject(hbmp)
            if "hdc_mem" in locals():
                win32gui.DeleteDC(hdc_mem)
            if "hdc" in locals():
                win32gui.ReleaseDC(0, hdc)

    def update_freq_panel(self):
        """Refresh the Top App list with current session data."""
        most_used, _ = self.get_app_freq_summary(top_n=5)
        
        # Reset visibility
        for row in self.app_rows:
            row["frame"].grid_remove()

        if not most_used:
            self.app_rows[0].frame.grid()
            self.app_rows[0].name.configure(text="No apps tracked yet this session.")
            self.app_rows[0].badge.configure(fg_color=BEE_GRAY, text="--")
            return

        for i, (exe, seconds, q_int, path) in enumerate(most_used):
            if i >= 5: break
            
            row = self.app_rows[i]
            row["frame"].grid()
            
            # Handle Icon (Optional: can be expanded with a proper HICON to PIL converter)
            icon_image = self._get_app_icon(path)
            if icon_image:
                row["icon"].configure(image=icon_image, text="")
            else:
                row["icon"].configure(image=None, text="📦")
            
            # Format EXE Name
            clean_name = exe.replace(".exe", "").capitalize()
            if len(clean_name) > 18: clean_name = clean_name[:15] + "..."
            
            row["name"].configure(text=clean_name)
            row["time"].configure(text=self.format_time(seconds))
            
            # Badge Color based on Quadrant
            color = Q_COLORS.get(q_int, BEE_GRAY)
            row["badge"].configure(text=f"Q{q_int+1}", fg_color=color)