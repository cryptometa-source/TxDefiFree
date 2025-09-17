import customtkinter as ctk
import tkinter as tk
import json
import copy

from TxDefi.UI.Components.ScrollableFrame import ScrollableFrame

class JsonEditorFrame(ScrollableFrame):
    def __init__(self, master, json_data: dict = None, **kwargs):
        super().__init__(master, **kwargs)
        self.entries = {}
        self.widgets = {}
        self.json_data = json_data
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        if self.json_data:
            self.reset_form(self.json_data)

    def reset_form(self, json_data: dict):               
        self.json_data = json_data

        self._rebuild_ui()

    def build_form(self, data, parent, path=()):
        if isinstance(data, dict):
            for key, value in data.items():
                full_path = path + (key,)
                row = parent.grid_size()[1]
                container = ctk.CTkFrame(parent)
                container.grid(row=row, column=0, sticky="ew", padx=10, pady=4)
                parent.grid_columnconfigure(0, weight=1)

                ctk.CTkLabel(container, text=key).grid(row=0, column=0, sticky="w")
                self._render_field(container, value, full_path, row=1)
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                full_path = path + (idx,)
                row = parent.grid_size()[1]

                frame = ctk.CTkFrame(parent)
                frame.grid(row=row, column=0, sticky="ew", padx=10, pady=2)
                parent.grid_columnconfigure(0, weight=1)
                self.widgets[full_path] = frame

                ctk.CTkLabel(frame, text=f"[{idx}]").grid(row=0, column=0, sticky="w")
                ctk.CTkButton(frame, text="✕", width=30, command=lambda p=path, i=idx: self._delete_list_item(p, i))\
                    .grid(row=0, column=1, padx=(5, 10))

                self._render_field(frame, item, full_path, row=0, column=2)

            # Add button
            row = parent.grid_size()[1]
            add_btn = ctk.CTkButton(parent, text="+ Add", width=70, command=lambda p=path: self._add_list_item(p))
            add_btn.grid(row=row, column=0, sticky="w", pady=4, padx=10)

    def _render_field(self, container, value, path, row=0, column=0):
        if isinstance(value, (dict, list)):
            self.build_form(value, container, path=path)
        else:
            entry = ctk.CTkEntry(container)
            entry.insert(0, str(value))
            entry.grid(row=row, column=column, sticky="ew", pady=2, padx=5)
            container.grid_columnconfigure(column, weight=1)
            self.entries[path] = entry

    def _get_data_by_path(self, path):
        data = self.json_data
        for key in path:
            data = data[key]
        return data

    def _set_data_by_path(self, path, value):
        data = self.json_data
        for key in path[:-1]:
            data = data[key]
        data[path[-1]] = value

    def _add_list_item(self, list_path):
        # Save current UI edits before modifying data
        self.json_data = self.get_json()

        parent_list = self._get_data_by_path(list_path)
        if parent_list:
            new_item = copy.deepcopy(parent_list[0])
        else:
            new_item = ""
        parent_list.append(new_item)
        self._rebuild_ui()

    def _delete_list_item(self, list_path, index):
        # Save current UI edits before modifying data
        self.json_data = self.get_json()

        parent_list = self._get_data_by_path(list_path)
        if 0 <= index < len(parent_list):
            parent_list.pop(index)
            self._rebuild_ui()

    def clear(self):
        # Destroy and rebuild with updated json_data
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        self.entries.clear()
        self.widgets.clear()
        
    def _rebuild_ui(self):
        self.clear()
        self.build_form(self.json_data, self.inner_frame)

    def get_json(self):
        def nested_set(container, keys, value):
            for i, key in enumerate(keys[:-1]):
                next_key = keys[i + 1]
                if isinstance(key, int):  # List index
                    while len(container) <= key:
                        container.append({} if isinstance(next_key, str) else [])
                    container = container[key]
                elif isinstance(container, dict):
                    if key not in container:
                        container[key] = {} if isinstance(next_key, str) else []
                    container = container[key]
            final_key = keys[-1]
            if isinstance(final_key, int):
                while len(container) <= final_key:
                    container.append(None)
                container[final_key] = value
            else:
                container[final_key] = value


        result = copy.deepcopy(self.json_data)
        for path, entry in self.entries.items():
            raw = entry.get()
            try:
                val = json.loads(raw)
            except:
                val = raw
            nested_set(result, path, val)
        return result

# Example usage
if __name__ == "__main__":
    import customtkinter as ctk
    import json

    example_json = {
        "strategy_name": "BundleStrategy",
        "limit_orders": [{"trigger_at_percent": 1, "allocation_percent": 100}],
        "stop_loss_orders": [{"trigger_at_percent": -80, "allocation_percent": 100}],
        "pubkeys": [{"pubkey": "1st key", "amount_in": 0.005}],
    }

    app = ctk.CTk()
    app.geometry("800x700")

    editor = JsonEditorFrame(app, json_data=example_json)
    editor.pack(fill="both", expand=True, padx=20, pady=20)

    def print_json():
        updated = editor.get_json()
        print(json.dumps(updated, indent=4))

    ctk.CTkButton(app, text="Print JSON", command=print_json).pack(pady=10)

    app.mainloop()