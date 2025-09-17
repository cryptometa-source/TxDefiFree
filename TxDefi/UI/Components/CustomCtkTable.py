from abc import abstractmethod
from pydoc import text
import customtkinter as ctk
import tkinter as tk
from TxDefi.UI.Components.CustomButtons import SwitchCallbackHandler, ToggleButton

class CtkTableCell(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, border_width=1, border_color="gray", **kwargs)
        self.inner_component : ctk.CTkBaseClass = None
    
    def clear(self):
        if self.inner_component:
            self.inner_component.destroy()

    def set_as_button(self, text: str, color: str, **kwargs)->ctk.CTkButton:
        self.clear()
        self.configure(fg_color="transparent")
        self.inner_component = ctk.CTkButton(self, text=text, fg_color=color, bg_color="transparent", border_width=1, border_color="black", **kwargs)
        self.inner_component.pack(fill="both", expand=True)

        return self.inner_component
    
    def set_as_toggle_button(self, id: int, callback_handler: SwitchCallbackHandler, on_text: str, off_text: str, color: str, **kwargs)->ctk.CTkButton:
        self.clear()
        self.inner_component = ToggleButton(self, id, callback_handler, on_text, off_text, fg_color=color, bg_color="transparent", border_width=1, border_color="black", **kwargs)
        self.inner_component.pack(fill="both", expand=True)

        return self.inner_component
    
    def set_as_label(self, text: str, **kwargs)->ctk.CTkLabel:
        self.clear()
        self.inner_component = ctk.CTkLabel(self, text=text, anchor="center", **kwargs)
        self.inner_component.pack(fill="both", expand=True)

        return self.inner_component

    def set_content(self, value: str, **kwargs):    
        if isinstance(self.inner_component, ToggleButton):      
            self.inner_component.toggle()
        elif isinstance(value, str) and isinstance(self.inner_component, ctk.CTkBaseClass):
            self.inner_component.configure(text=value, **kwargs)

class CustomCtkTable(ctk.CTkFrame):
    def __init__(self, master, columns: dict, **kwargs):
        """
        columns: list of dicts. Each dict defines:
            - "header": str
            - "type": "string" | "checkbox" | "button"
            - "button_text" (optional): default text for buttons
            - "image" (optional): path to image file (for buttons only)
            - "command" (optional): callable (for buttons only)
        """
        super().__init__(master, **kwargs)
        self.columns = columns
        self.rows : dict[str, list[CtkTableCell]] = {}
        self.column_count = len(columns)
        self.selected_row = None
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create canvas + scrollbar
        self.canvas = tk.Canvas(self, borderwidth=0, background="#2b2b2b", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar_h = ctk.CTkScrollbar(self, orientation="horizontal", command=self.canvas.xview)
        self.scrollbar_h.grid(row=1, column=0, sticky="ew")
        
        self.scrollbar_v = ctk.CTkScrollbar(self, orientation="vertical", command=self.canvas.yview)
        self.scrollbar_v.grid(row=0, column=1, sticky="ns")

        self.scrollable_frame = ctk.CTkFrame(self.canvas)
        self.canvas.configure(xscrollcommand=self.scrollbar_h.set, yscrollcommand=self.scrollbar_v.set)

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Add headers inside scrollable frame
        for idx, col in enumerate(columns):            
            created_cell = CtkTableCell(self.scrollable_frame, bg_color = self._bg_color)
            created_cell.set_as_label(col["header"], bg_color=created_cell._bg_color, fg_color=created_cell._fg_color, font=ctk.CTkFont(weight="bold"))
            created_cell.grid(row=0, column=idx, padx=1, pady=(0, 10), sticky="nsew")
            self.scrollable_frame.grid_columnconfigure(idx, weight=1)

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def insert_row(self, id: str | int, items : list[CtkTableCell]):
        """
        values: list of values corresponding to column types
            for 'string': string
            for 'checkbox': bool
            for 'button': overrides button text (optional)
        """
        if id not in self.rows:
            row_widgets = []
            row_index = len(self.rows) + 1  # +1 because row 0 is header

            for col_index, col in enumerate(self.columns):
                col_type = col["type"]
                ui_component = items[col_index]
                ui_component.grid(row=row_index, column=col_index, padx=0, pady=0, sticky="nsew")
            
                row_widgets.append(ui_component)
                        
            self.rows[id] = row_widgets

    def update_item_column(self, id: str | int, column: int, value, **kwargs):
        row = self.rows.get(id)

        if row and column < len(row):
            component = row[column]
            component.set_content(value, **kwargs)

    def delete_row(self, id: str):
        if id in self.rows:
            cells = self.rows.pop(id)

            for widget in cells:
                widget.destroy()

            # Shift remaining rows up in the grid
            rows_list = list(self.rows.values())
            for i in range(len(rows_list)):
                for col_index, widget in enumerate(rows_list[i]):
                    widget.grid_configure(row=i + 1) # +1 because row 0 is header

    def highlight_row(self, row_index):
        # Clear previous selection
        if self.selected_row is not None:
            self.set_row_color(self.selected_row, "transparent")

        # Highlight new row
        self.set_row_color(row_index, "#1f6aa5")  # CustomTkinter blue highlight
        self.selected_row = row_index

    def set_row_color(self, row_index, color):
        for widget in self.grid_frame.grid_slaves(row=row_index):
            widget.configure(fg_color=color)

# Example usage
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.geometry("600x400")

    def on_click():
        print("Button clicked!")

    table = CustomCtkTable(root, columns=[
        {"header": "Created", "type": "string"},
        {"header": "Name", "type": "string"},
        {"header": "Status", "type": "string"},
        {"header": "Action", "type": "button"},
        {"header": "", "type": "x"}
    ])
    table.pack(fill="both", expand=True, padx=20, pady=20)

    # Add some rows
    #table.insert_row("1", ["178388388", "Alice", "status", ToggleButton(table.scrollable_frame, ClickCallbackHandler("1")), None])
    #table.insert_row("2", ["178388388", "Bob", "status", ToggleButton(table.scrollable_frame, ClickCallbackHandler("2")), None])
    #table.insert_row("3", ["178388388", "Charlie", "status", ToggleButton(table.scrollable_frame, ClickCallbackHandler("3")), None])

    root.mainloop()
