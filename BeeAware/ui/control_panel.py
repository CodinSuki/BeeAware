# ui/control_panel.py
# Mixin providing build_control_panel() for BeewareApp.

import customtkinter as ctk
from config import (
    BEE_AMBER, BEE_AMBER_DIM, BEE_COMB, BEE_COMB_MID,
    BEE_BROWN, BEE_CREAM, BEE_GRAY, BEE_RED,
)

class ControlPanelMixin:

    def build_control_panel(self):
        frame = ctk.CTkFrame(self, height=70, corner_radius=10, fg_color=BEE_COMB_MID)
        frame.grid(row=0, column=0, columnspan=2, padx=20, pady=(16, 0), sticky="ew")
        frame.grid_propagate(False)
   
        frame.grid_columnconfigure(4, weight=1)

        self.btn_toggle = ctk.CTkButton(
            frame, text="Start Session", width=150, height=38,
            fg_color=BEE_AMBER, hover_color=BEE_AMBER_DIM, text_color=BEE_COMB,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.toggle_tracking,
        )
        self.btn_toggle.grid(row=0, column=0, padx=(16, 8), pady=16)

        self.btn_pause = ctk.CTkButton(
            frame, text="Privacy Pause", width=130, height=38,
            fg_color=BEE_BROWN, hover_color=BEE_COMB_MID, text_color=BEE_CREAM,
            font=ctk.CTkFont(size=13),
            state="disabled", command=self.toggle_pause,
        )
        self.btn_pause.grid(row=0, column=1, padx=8, pady=16)

        self.btn_graphs = ctk.CTkButton(
            frame, text="Hide Charts", width=130, height=38,
            fg_color=BEE_COMB_MID, hover_color=BEE_BROWN, text_color=BEE_CREAM,
            font=ctk.CTkFont(size=13),
            command=self.toggle_graphs,
        )
        self.btn_graphs.grid(row=0, column=2, padx=8, pady=16)

       
        self.btn_options = ctk.CTkButton(
            frame, 
            text="⚙ Options",
            command=self.open_options,
            fg_color=BEE_BROWN,       
            hover_color=BEE_COMB_MID,
            width=100, height=38,
            font=ctk.CTkFont(size=13)
        )
        self.btn_options.grid(row=0, column=3, padx=8, pady=16) 

      
        status_box = ctk.CTkFrame(frame, fg_color="transparent")
        status_box.grid(row=0, column=4, padx=16, sticky="w")

        self.dot_status = ctk.CTkLabel(
            status_box, text="●", text_color=BEE_GRAY, font=ctk.CTkFont(size=12),
        )
        self.dot_status.pack(side="left", padx=(0, 6))

        self.lbl_status = ctk.CTkLabel(
            status_box, text="IDLE",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=BEE_GRAY,
        )
        self.lbl_status.pack(side="left")

       
        ctk.CTkLabel(
            frame, text=self.ai_status,
            font=ctk.CTkFont(size=11),
            text_color=BEE_GRAY if self.models_ready else BEE_RED,
        ).grid(row=0, column=5, padx=16, sticky="e")