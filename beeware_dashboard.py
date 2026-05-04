import customtkinter as ctk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta
import os


ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue")

class BeewareDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Beeware | Personal Productivity Analytics")
        self.geometry("1000x600")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
       
        self.today_stats, self.yesterday_stats = self.load_data()
        
  
        self.build_summary_panel()
        self.build_graphs_panel()

    def load_data(self):
        """Reads the CSV, groups by day, and extracts Today vs Yesterday."""
        file_path = "data/beeware_daily_log.csv"
        
       
        empty_stats = {'q1_urgent': 0, 'q2_growth': 0, 'q3_noise': 0, 'q4_play': 0}
        
        if not os.path.exists(file_path):
            return empty_stats, empty_stats
            
        try:
            df = pd.read_csv(file_path)
         
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            
           
            daily_totals = df.groupby('date')[['q1_urgent', 'q2_growth', 'q3_noise', 'q4_play']].sum()
            
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
          
            today_data = daily_totals.loc[today].to_dict() if today in daily_totals.index else empty_stats
            yesterday_data = daily_totals.loc[yesterday].to_dict() if yesterday in daily_totals.index else empty_stats
            
            return today_data, yesterday_data
            
        except Exception as e:
            print(f"Data loading error: {e}")
            return empty_stats, empty_stats

    def build_summary_panel(self):
        """The left column: Text summaries and the Delta Analysis."""
        frame = ctk.CTkFrame(self, corner_radius=15)
        frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        header = ctk.CTkLabel(frame, text="Daily Verdict", font=ctk.CTkFont(size=24, weight="bold"))
        header.pack(pady=(20, 10))
        
   
        today_productive = (self.today_stats['q1_urgent'] + self.today_stats['q2_growth']) / 60
        today_distracted = (self.today_stats['q3_noise'] + self.today_stats['q4_play']) / 60
        
        yesterday_distracted = (self.yesterday_stats['q3_noise'] + self.yesterday_stats['q4_play']) / 60
        
  
        if yesterday_distracted > 0:
            delta = ((today_distracted - yesterday_distracted) / yesterday_distracted) * 100
            if delta > 0:
                delta_text = f"Distractions are UP {abs(delta):.1f}% from yesterday. Focus!"
                delta_color = "#ff6b6b"
            else:
                delta_text = f"Distractions are DOWN {abs(delta):.1f}%! Great job."
                delta_color = "#51cf66"
        else:
            delta_text = "Not enough data from yesterday for comparison."
            delta_color = "gray"

        ctk.CTkLabel(frame, text=f"Focus Time: {today_productive:.1f} mins", font=ctk.CTkFont(size=18)).pack(pady=10)
        ctk.CTkLabel(frame, text=f"Noise/Play Time: {today_distracted:.1f} mins", font=ctk.CTkFont(size=18)).pack(pady=10)
        
   
        verdict_box = ctk.CTkTextbox(frame, height=80, text_color=delta_color, font=ctk.CTkFont(size=16))
        verdict_box.pack(pady=20, padx=20, fill="x")
        verdict_box.insert("0.0", f">> AI ANALYSIS:\n{delta_text}")
        verdict_box.configure(state="disabled")

    def build_graphs_panel(self):
        """The right column: Matplotlib embedded charts."""
        frame = ctk.CTkFrame(self, corner_radius=15)
        frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        

        plt.style.use('dark_background')
        
     
        fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
        fig.patch.set_facecolor('#2b2b2b') 
        ax.set_facecolor('#2b2b2b')
        
        labels = ['Urgent', 'Growth', 'Noise', 'Play']
        sizes = [
            self.today_stats['q1_urgent'],
            self.today_stats['q2_growth'],
            self.today_stats['q3_noise'],
            self.today_stats['q4_play']
        ]
        
      
        colors = ['#339af0', '#51cf66', '#fcc419', '#ff6b6b'] 
        

        if sum(sizes) > 0:
            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
            ax.set_title("Today's Breakdown", color="white")
        else:
            ax.text(0.5, 0.5, "No Data Yet Today", horizontalalignment='center', verticalalignment='center', color='white')
            ax.axis('off')


        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(pady=20, padx=20, fill="both", expand=True)


if __name__ == "__main__":
    app = BeewareDashboard()
    app.mainloop()