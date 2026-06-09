import os
import json
import customtkinter as ctk
import config

from config import BEE_AMBER, BEE_AMBER_DIM, BEE_COMB, BEE_COMB_LIGHT, BEE_COMB_MID, BEE_CREAM, BEE_RED, BEE_GRAY

class RulesManagerWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Rules & Exclusions Manager")
        self.geometry("450x500")
        self.configure(fg_color=BEE_COMB)
        self.attributes("-topmost", True)
        self.grab_set()  

        # Setup Tabview
        self.tabview = ctk.CTkTabview(
            self, 
            fg_color=BEE_COMB_LIGHT, 
            segmented_button_selected_color=BEE_AMBER, 
            segmented_button_selected_hover_color=BEE_AMBER_DIM
        )
        self.tabview.pack(expand=True, fill="both", padx=15, pady=15)

        self.tab_corr = self.tabview.add("Quadrant Corrections")
        self.tab_idle = self.tabview.add("Ignored / Idle")

        # Scrollable frames for the lists
        self.scroll_corr = ctk.CTkScrollableFrame(self.tab_corr, fg_color="transparent")
        self.scroll_corr.pack(expand=True, fill="both")

        self.scroll_idle = ctk.CTkScrollableFrame(self.tab_idle, fg_color="transparent")
        self.scroll_idle.pack(expand=True, fill="both")

        self.refresh_lists()

    def refresh_lists(self):
        # Clear existing rows first
        for widget in self.scroll_corr.winfo_children(): widget.destroy()
        for widget in self.scroll_idle.winfo_children(): widget.destroy()

        #Populate Corrections Tab
        for key, val in list(config.CUSTOM_OVERRIDES.items()):
            row = ctk.CTkFrame(self.scroll_corr, fg_color=BEE_COMB_MID, corner_radius=6)
            row.pack(fill="x", pady=2, padx=4)
            
            
            ctk.CTkLabel(
                row, 
                text=f"{key}  →  Q{val + 1}", 
                text_color=BEE_CREAM, 
                font=ctk.CTkFont(size=12, weight="bold")
            ).pack(side="left", padx=10, pady=6)
            
            btn_del = ctk.CTkButton(
                row, 
                text="✕", width=28, height=24, 
                fg_color=BEE_RED, hover_color="#8f3f30",
                command=lambda k=key: self.delete_override(k)
            )
            btn_del.pack(side="right", padx=6)

        #Populate Idle / System Tab
        for exe in list(config.IDLE_EXES):
            self._build_idle_row(exe, "exe")
        for title in list(config.IDLE_TITLES):
            self._build_idle_row(title, "title")

    def _build_idle_row(self, item, item_type):
        row = ctk.CTkFrame(self.scroll_idle, fg_color=BEE_COMB_MID, corner_radius=6)
        row.pack(fill="x", pady=2, padx=4)
        
        prefix = "[EXE]" if item_type == "exe" else "[TITLE]"
        ctk.CTkLabel(
            row, 
            text=f"{prefix} {item}", 
            text_color=BEE_GRAY, 
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=10, pady=6)
        
        btn_del = ctk.CTkButton(
            row, 
            text="✕", width=28, height=24, 
            fg_color=BEE_RED, hover_color="#8f3f30",
            command=lambda i=item, t=item_type: self.delete_idle(i, t)
        )       
        btn_del.pack(side="right", padx=6)

    def _save_overrides(self):
        """Write CUSTOM_OVERRIDES to overrides.json."""
        path = os.path.abspath(config.OVERRIDES_JSON_PATH)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config.CUSTOM_OVERRIDES, f, indent=4)
        except OSError as e:
            print(f"[RulesManager] Failed to save overrides: {e}")

    def _save_idle_exclusions(self):
        """Write IDLE_EXES and IDLE_TITLES to idle_exclusions.json."""
        path = os.path.abspath(config.IDLE_EXCLUSIONS_PATH)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "idle_exes":   sorted(config.IDLE_EXES),
                    "idle_titles": sorted(config.IDLE_TITLES),
                }, f, indent=4)
        except OSError as e:
            print(f"[RulesManager] Failed to save idle exclusions: {e}")

 

    def delete_override(self, key):
        if key in config.CUSTOM_OVERRIDES:
            del config.CUSTOM_OVERRIDES[key]
        self._save_overrides()
        self.refresh_lists()

    def delete_idle(self, item, item_type):
        if item_type == "exe":
            config.IDLE_EXES.discard(item)
        elif item_type == "title":
            config.IDLE_TITLES.discard(item)
        self._save_idle_exclusions()
        self.refresh_lists()