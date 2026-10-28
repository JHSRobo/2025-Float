import tkinter as tk
from tkinter import ttk, Toplevel
import tkinter.font as tkfont
import requests
import json
from datetime import datetime

#plot
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MaxNLocator
from matplotlib.ticker import FormatStrFormatter
import scienceplots

ESP32_AP_IP = "192.168.4.1"
ctrl_endpoint = f"http://{ESP32_AP_IP}/ctrl"
data_endpoint = f"http://{ESP32_AP_IP}/data"
piddata_endpoint = f"http://{ESP32_AP_IP}/piddata"
company_name = 'JHS'

def center_window(window):
    window.update_idletasks()
    window_width = window.winfo_width()
    window_height = window.winfo_height()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    window.geometry(f"+{x}+{y}")

class FloatControlCenter:
    def __init__(self, root):
        self.field_vars = {}
        self.root = root
        self.root.title("Float Control Center")
        self.root.geometry("800x700")
        
        # Create notebook (tabs)
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=("Arial", 16))
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(padx=10, pady=10, expand=True, fill="both")
        
        # Create tabs
        title_font = tkfont.Font(family="Arial", size=18, weight="bold")
        self.profiling_tab = ttk.Frame(self.notebook)
        self.config_tab = ttk.Frame(self.notebook)        
        self.manual_tab = ttk.Frame(self.notebook)        

        self.notebook.add(self.profiling_tab, text="  Profiling  ")
        self.notebook.add(self.config_tab, text="  Configuration  ")        
        self.notebook.add(self.manual_tab, text="  Manual Control  ")
        
        field_name = "app_status"
        self.field_vars[field_name] = tk.StringVar()
        app_status = ttk.Label(root, textvariable=self.field_vars[field_name])
        app_status.configure(foreground="blue")
        app_status.pack(side="left")

        self.setup_config_tab()
        self.setup_profiling_tab()
        self.setup_manual_tab()

        center_window(self.root)
        
    def setup_config_tab(self):
        # Create and grid a frame for better organization
        config_frame = ttk.Frame(self.config_tab)
        config_frame.pack(padx=10, pady=10, fill="both")
        # Config fields
        ttk.Button(config_frame, text="Retrieve Float Config", command=self.get_config_vars).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(config_frame, text="Update Float Config", command=self.set_config_vars).grid(row=0, column=2, padx=5, pady=5)
        
        field_name = "Company Name"
        self.field_vars[field_name] = tk.StringVar()
        ttk.Label(config_frame, text=f"{field_name}:").grid(row=2, column=1, padx=5, pady=5, sticky="e")
        ttk.Entry(config_frame, textvariable=self.field_vars[field_name], width=20).grid(row=2, column=2, padx=5, pady=5, sticky="w")
        field_name = "Max Profiling Time"
        self.field_vars[field_name] = tk.StringVar()
        ttk.Label(config_frame, text=f"{field_name} (s):").grid(row=3, column=1, padx=5, pady=5, sticky="e")
        ttk.Entry(config_frame, textvariable=self.field_vars[field_name], width=10).grid(row=3, column=2, padx=5, pady=5, sticky="w")
        field_name = "Target Depth"
        self.field_vars[field_name] = tk.StringVar()
        ttk.Label(config_frame, text=f"{field_name} (m):").grid(row=4, column=1, padx=5, pady=5, sticky="e")
        ttk.Entry(config_frame, textvariable=self.field_vars[field_name], width=10).grid(row=4, column=2, padx=5, pady=5, sticky="w")
        field_name = "Target Depth Tolerance"
        self.field_vars[field_name] = tk.StringVar()
        ttk.Label(config_frame, text=f"{field_name} (m):").grid(row=5, column=1, padx=5, pady=5, sticky="e")
        ttk.Entry(config_frame, textvariable=self.field_vars[field_name], width=5).grid(row=5, column=2, padx=5, pady=5, sticky="w")
        field_name = "Current Depth"
        self.field_vars[field_name] = tk.StringVar()
        ttk.Label(config_frame, text=f"{field_name} (m):").grid(row=6, column=1, padx=5, pady=5, sticky="e")
        ttk.Entry(config_frame, state="readonly", textvariable=self.field_vars[field_name], width=10).grid(row=6, column=2, padx=5, pady=5, sticky="w")
        field_name = "Float ESP32 IP"
        self.field_vars[field_name] = tk.StringVar()
        ttk.Label(config_frame, text=f"{field_name}:", ).grid(row=7, column=1, padx=5, pady=5, sticky="e")
        ttk.Entry(config_frame, state="readonly", textvariable=self.field_vars[field_name], width=20).grid(row=7, column=2, padx=5, pady=5, sticky="w")
            
    def get_config_vars(self):
        global company_name
        params = {"command":"GETCONFIG"}
        resp = requests.get(ctrl_endpoint, params=params, timeout=30)
        if (resp.status_code == 200):
            print(resp.text)
            config_setting = json.loads(resp.text)
            for field, value in config_setting.items():
                self.field_vars[field].set(value)
            company_name = self.field_vars["Company Name"].get()
            self.field_vars["app_status"].set("Get config settings successfully.")
        else:
            self.field_vars["app_status"].set(f"Get config settings failed. Error {resp.text}")

    def set_config_vars(self):    
        msg="command=config&";    
        for field, var in self.field_vars.items():
            msg+=f"{field}={var.get()}&"
        print(msg)
        params = {"command": "SETCONFIG",
                  "Company Name": self.field_vars["Company Name"].get(),
                  "Max Profiling Time": self.field_vars["Max Profiling Time"].get(),
                  "Target Depth": self.field_vars["Target Depth"].get(),
                  "Target Depth Tolerance": self.field_vars["Target Depth Tolerance"].get()
                  }
        print(params)
        resp=requests.get(ctrl_endpoint, params, timeout=30)
        if (resp.status_code == 200):
            print("config setting updated")            
            self.field_vars["app_status"].set("Set config settings successfully.")
        else:
            self.field_vars["app_status"].set(f"Set config settings failed. Error {resp.text}")

    def setup_profiling_tab(self):
        # Top frame for buttons and inputs
        top_frame = ttk.Frame(self.profiling_tab)
        top_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Bottom frame for text output
        middle_frame = ttk.Frame(self.profiling_tab, relief="groove")
        middle_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Bottom frame for text output
        bottom_frame = ttk.Frame(self.profiling_tab, relief="groove")
        bottom_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        
        # Status section
        ttk.Button(top_frame, text="Status", width=15, command=self.get_status).grid(row=1, column=1, padx=5, pady=5, sticky="e")
        self.field_vars["Status"] = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.field_vars["Status"], width=50).grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        
        # PID section
        ttk.Button(top_frame, text="Start Profiling", command=self.send_start_profiling, width=15).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        pid_frame = ttk.Frame(top_frame)
        pid_frame.grid(row=2, column=2)        
        ttk.Label(pid_frame, text="p:").grid(row=0, column=1, padx=5, pady=5, sticky="e")
        self.field_vars["p"] = tk.StringVar()
        ttk.Entry(pid_frame, textvariable=self.field_vars["p"], width=10).grid(row=0, column=2, padx=5, pady=5, sticky="w")  
        ttk.Label(pid_frame, text="i:").grid(row=0, column=3, padx=5, pady=5, sticky="e")
        self.field_vars["i"] = tk.StringVar()
        ttk.Entry(pid_frame, textvariable=self.field_vars["i"], width=10).grid(row=0, column=4, padx=5, pady=5, sticky="w")
        ttk.Label(pid_frame, text="d:").grid(row=0, column=5, padx=5, pady=5, sticky="e")
        self.field_vars["d"] = tk.StringVar()
        ttk.Entry(pid_frame, textvariable=self.field_vars["d"], width=10).grid(row=0, column=6, padx=5, pady=5, sticky="w")
        # Data buttons
        button_frame = ttk.Frame(top_frame)
        button_frame.grid(row=3, column=2)
        ttk.Button(button_frame, text="Retrieve Data", command=self.retrieve_profile_data, width=15).grid(row=0, column=1, padx=5, pady=5, sticky="e")
        ttk.Button(button_frame, text="Retrieve PID Data", command=self.retrieve_pid_data, width=15).grid(row=0, column=2, padx=5, pady=5, sticky="e")
        ttk.Button(button_frame, text="Plot Data", command=self.plot_data, width=15).grid(row=0, column=3, padx=5, pady=5, sticky="e")
        ttk.Button(button_frame, text="Clear Data", command=self.clear_data, width=15).grid(row=0, column=4, padx=5, pady=5, sticky="e")
        
        # Text output with scrollbar
        text_frame = ttk.Frame(middle_frame)
        text_frame.pack(fill="both", expand=True)
        
        text_scrollbar = ttk.Scrollbar(text_frame)
        text_scrollbar.pack(side="right", fill="y")
        
        self.data_text = tk.Text(text_frame, height=14, width=40, yscrollcommand=text_scrollbar.set)
        self.data_text.pack(fill="both", expand=True)
        text_scrollbar.config(command=self.data_text.yview)

        # tree view for PID data
        tree_view_frame = ttk.Frame(bottom_frame)        
        tree_view_frame.pack(fill="both", expand=True)
        # Define column headers
        columns = ("Time", "Prev Time", "Time Step", "Depth", "Error", "Integral", "Derivative", "Control")
        self.pid_tree = ttk.Treeview(tree_view_frame, columns=columns, show="headings", height=12)

        # Set column headings and configure column properties
        for col in columns:
            self.pid_tree.heading(col, text=col)
            self.pid_tree.column(col, width=90, anchor="center")

        # Add a scrollbar
        tree_scrollbar = ttk.Scrollbar(tree_view_frame, orient="vertical", command=self.pid_tree.yview)
        self.pid_tree.configure(yscroll=tree_scrollbar.set)

        # Place the Treeview and scrollbar in the window
        self.pid_tree.grid(row=0, column=0, sticky="nsew")
        tree_scrollbar.grid(row=0, column=1, sticky="ns")

        # Make the grid expandable
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

    def get_status(self):
        global company_name
        params = {"command":"STATUS"}
        resp = requests.get(ctrl_endpoint, params=params, timeout=30)
        if (resp.status_code == 200):
            print(resp.text)
            self.field_vars["Status"].set(resp.text)
            tokens = resp.text.split(" ")
            company_name = tokens[0]
            self.field_vars["p"].set(tokens[8])
            self.field_vars["i"].set(tokens[10])
            self.field_vars["d"].set(tokens[12])
            self.field_vars["app_status"].set("Get status successfully.")
        else:
            self.field_vars["app_status"].set(f"Get status failed. Error {resp.text}")

    def retrieve_profile_data(self):
        resp = requests.get(data_endpoint, timeout=30)
        if (resp.status_code == 200):
            #self.profile_data = resp.text
            print(resp.text)
            self.profile_data_file_name = f"float_profile_data_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}"
            data_file = open(self.profile_data_file_name, "w")
            data_file.write(resp.text)
            data_file.close()
            #display data
            self.display_profile_data()                       
            self.field_vars["app_status"].set("Retrieve data successfully.")
        else:
            self.field_vars["app_status"].set(f"Retrieve data failed. Error {resp.text}")
        
    def display_profile_data(self):
        col_names = ['Company', 'Time', 's', 'Pressure', 'kpa', 'Depth', 'm']
        df = pd.read_csv(self.profile_data_file_name, header=None, sep=' ', 
                        names=col_names, usecols=['Time', 'Pressure', 'Depth'])
        #print(df.head(100))
        # #df['Depth'] += depth_offset
        df['Time'] -= df['Time'].iloc[0]
        df.set_index('Time', inplace=True)         
        # #df with every second data, interpolated when it is not there
        df_one_sec = df.reindex(range(df.index.min(), df.index.max() + 1)).interpolate(method='linear')
        # #df with every 5-second data
        df_five_sec = df_one_sec.loc[df_one_sec.index % 5 == 0]
        
        self.data_text.delete(1.0, tk.END)
        for index, row in df_five_sec.iterrows():
            self.data_text.insert(tk.END, 
                f"{company_name} {index} s {row['Pressure']:.2f} kpa {row['Depth']:.2f} m\n")

        self.profile_data = df_five_sec #used by plot

    def retrieve_pid_data(self):                    
        resp = requests.get(piddata_endpoint, timeout=30)
        if (resp.status_code == 200):            
            print(resp.text)
            output_file = open(f"PID_data_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}", "w")
            output_file.write(resp.text)
            output_file.close()
            data = json.loads(resp.text)
            for item in self.pid_tree.get_children():
                self.pid_tree.delete(item)

            for item in data:
                values = (
                    f"{item.get('Time', 0)}",
                    f"{item.get('Prev Time', 0)}",
                    f"{item.get('Time Ttep', 0.0):.2f}",
                    f"{item.get('Depth', 0.0):.2f}",
                    f"{item.get('Error', 0.0):.2f}",
                    f"{item.get('Integral', 0.0):.2f}",
                    f"{item.get('Derivative', 0.0):.2f}",
                    f"{item.get('Control', 0.0):.2f}"
                )
                self.pid_tree.insert("", "end", values=values)
            self.field_vars["app_status"].set("Get PID data successfully.")
        else:
            self.field_vars["app_status"].set(f"Get PID data failed. Error {resp.text}")
        
    def plot_data(self):
        popup = Toplevel(self.root)
        popup.title("Jesuit High School - P.O.D. - Profile Data")
        popup.geometry("1000x500")  # Set the size of the popup window

        plt.style.use(["science", "grid", "notebook"])
        plt.rcParams["font.family"] = "Times New Roman"            
        fig, axes = plt.subplots(1, 1, figsize=(12,5))
        #marker is o, line is dash, ls=line width, ms=marker size
        axes.plot(self.profile_data.index, self.profile_data['Depth'], 'o--', color='darkblue', lw=0.7, ms=5.0)
        axes.set_title(f"JHS - P.O.D - Profile Data", fontsize=20, fontweight="bold", color="darkblue", y=1.05)
        axes.set_xlabel("Time (seconds)")
        axes.set_ylabel("Depth (meters)")
        axes.set_xlim(left=0)
        axes.set_ylim(bottom=0)
        axes.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
        axes.set_xticks(self.profile_data.index)
        axes.xaxis.set_ticks_position("bottom")
        axes.yaxis.set_ticks_position("left")
        # #invert y-axis
        axes.invert_yaxis()
        # axes.xaxis.tick_top()
        
        # Embed the matplotlib figure in the Tkinter popup window
        canvas = FigureCanvasTkAgg(fig, master=popup)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        center_window(canvas)

    def clear_data(self):        
        self.data_text.delete("1.0", tk.END)
        for item in self.pid_tree.get_children():
            self.pid_tree.delete(item)

    def send_start_profiling(self):
        self.clear_data()

        params = {"command":"START",
                  "p": self.field_vars["p"].get(),
                  "i": self.field_vars["i"].get(),
                  "d": self.field_vars["d"].get()}
        resp = requests.get(ctrl_endpoint, params=params, timeout=30)
        if (resp.status_code == 200):
            print(resp.text)
            self.field_vars["app_status"].set("Start profiling successfully.")
        else:
            self.field_vars["app_status"].set(f"Start profiling failed. Error {resp.text}")

    def setup_manual_tab(self):
        manual_frame = ttk.Frame(self.manual_tab)
        manual_frame.pack(padx=10, pady=10, fill="both")
        
        # Up control
        ttk.Button(manual_frame, text="Up", command=self.go_up, width=15).grid(row=1, column=1, padx=5, pady=5, sticky="e")
        self.field_vars["Up Seconds"] = tk.StringVar()
        ttk.Entry(manual_frame, textvariable=self.field_vars["Up Seconds"], width=10).grid(row=1, column=2, padx=5, pady=5, sticky="w")
        ttk.Label(manual_frame, text="Seconds").grid(row=1, column=3, padx=5, pady=5, sticky="w")
        
        # Down control
        ttk.Button(manual_frame, text="Down", command=self.go_down, width=15).grid(row=2, column=1, padx=5, pady=5, sticky="e")
        self.field_vars["Down Seconds"] = tk.StringVar()
        ttk.Entry(manual_frame, textvariable=self.field_vars["Down Seconds"], width=10).grid(row=2, column=2, padx=5, pady=5, sticky="w")
        ttk.Label(manual_frame, text="Seconds").grid(row=2, column=3, padx=5, pady=5, sticky="w")

        # Control buttons        
        ttk.Button(manual_frame, text="Reset ESP32", command=self.reset_ESP32, width=15).grid(row=3, column=1, padx=5, pady=5, sticky="")

    def go_down(self):
        params = {"command":"DOWN", "seconds":self.field_vars["Down Seconds"].get()}
        resp = requests.get(ctrl_endpoint, params=params, timeout=30)
        if (resp.status_code == 200):
            print(resp.text)
            self.field_vars["app_status"].set("Go down successfully.")
        else:
            self.field_vars["app_status"].set(f"Go down failed. Error {resp.text}")

    def go_up(self):
        params = {"command":"UP", "seconds":self.field_vars["Up Seconds"].get()}
        resp = requests.get(ctrl_endpoint, params=params, timeout=30)
        if (resp.status_code == 200):
            print(resp.text)
            self.field_vars["app_status"].set("Go up successfully.")
        else:
            self.field_vars["app_status"].set(f"Go up failed. Error {resp.text}")

    def reset_ESP32(self):
        params = {"command":"RESET"}
        resp = requests.get(ctrl_endpoint, params=params, timeout=30)
        if (resp.status_code == 200):
            print(resp.text)
            self.field_vars["app_status"].set("Reset ESP32 successfully.")
        else:
            self.field_vars["app_status"].set(f"Reset EPS32 failed. Error {resp.text}")

def main():
    root = tk.Tk()
    app = FloatControlCenter(root)
    icon_image = tk.PhotoImage(file="jesuit-logo.gif")
    root.iconphoto(True, icon_image)
    root.mainloop()

if __name__ == "__main__":
    main()