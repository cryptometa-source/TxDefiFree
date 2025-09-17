from sys import platform
import tkinter as tk
import customtkinter as ctk
import os
import sys

sys.path.insert(1, os.getcwd()) #needed to access resources outside this fold

class CustomWindow(ctk.CTkToplevel):
    def __init__(self, parent, title: str, icon_path: str = None, **kargs):
        super().__init__(parent, **kargs)
        self.title(title)

        self.update_idletasks()

        # Override close button to hide the window instead
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
    
        if icon_path:            
            self.config_icon = tk.PhotoImage(file=icon_path) #TODO Use the config icon
            if platform.startswith("win"):
                self.after(200, lambda: self.iconphoto(False, self.config_icon))   
        
        self.withdraw()

    def resize_window(self, padx = 0, pady = 0):
        self.geometry(f"{self.winfo_reqwidth() + padx}x{self.winfo_reqheight() + pady}")

    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        self.geometry(f"{width}x{height}+{x}+{y}")

    def show_window(self):
        self.deiconify()
        self.lift()  # Bring to front
        self.attributes("-topmost", True)
        self.focus_force()