import customtkinter as ctk
import tkinter as tk

class ScrollableFrame(ctk.CTkFrame):
    def __init__(self, parent, width=400, height=300, *args, **kwargs):
        super().__init__(parent, width=width, height=height, *args, **kwargs)
        # Store width and height
        self.frame_width = width
        self.frame_height = height
     
        # Get the correct background color for the current theme
        if isinstance(self._bg_color, list):  # If it's a tuple (light mode, dark mode)
            bg_color = self._bg_color[0] if ctk.get_appearance_mode() == "Light" else self._bg_color[1]
        else:
            bg_color = self._bg_color

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Create a canvas and a scrollbar
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0, width=self.frame_width, height=self.frame_height)
        self.h_scrollbar = ctk.CTkScrollbar(self, orientation="horizontal", command=self.canvas.xview)
        self.v_scrollbar = ctk.CTkScrollbar(self, orientation="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)

        # Pack canvas and scrollbar
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")

        # Create an inner frame inside the canvas
        self.inner_frame = ctk.CTkFrame(self.canvas, bg_color=self._bg_color, fg_color="transparent")  
        self.frame_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw", width=self.frame_width)

        # Bind resizing events
        self.inner_frame.bind("<Configure>", self.update_scroll_region)
        self.canvas.bind("<Configure>", self.resize_frame)
        self.bind_mouse_wheel()

    def bind_mouse_wheel(self):
        """ Enable scrolling with the mouse wheel """
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)  # Windows/Mac
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)  # Linux (scroll up)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)  # Linux (scroll down)

    def _on_mousewheel(self, event):
        focused_widget = self.canvas.winfo_toplevel().focus_get()

        if self.canvas == focused_widget:
            """ Scroll the canvas when the mouse wheel moves """
            if event.num == 4:  # Linux Scroll Up
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:  # Linux Scroll Down
                self.canvas.yview_scroll(1, "units")
            else:  # Windows/Mac Scroll
                self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def update_scroll_region(self, event=None):
        """ Update scroll region when content changes """
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def resize_frame(self, event):        
        """ Adjust frame width to match canvas width dynamically """
        self.canvas.itemconfig(self.frame_id, width=event.width)

#Main application
#root = ctk.CTk()
#root.geometry("500x400")
#
#scrollable_frame = ScrollableFrame(root, width=50, height=20)
#scrollable_frame.pack(pady=20, padx=20, fill="both", expand=True)
#
## Add many widgets inside the scrollable frame
#for i in range(30):
#    label = ctk.CTkLabel(scrollable_frame.inner_frame, text=f"Item {i+1}")
#    label.grid(row=i, column=0, sticky="w", pady=5)
#
#root.mainloop()
