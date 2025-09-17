import threading
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import time
from PIL import ImageFont
from TxDefi.Data.MarketEnums import StrategyState
from TxDefi.Managers.TradesManager import TradesManager
from TxDefi.UI.Components.CustomButtons import SwitchCallbackHandler, ToggleButton
from TxDefi.UI.Components.CustomCtkTable import CtkTableCell, CustomCtkTable
from TxDefi.UI.Components.JsonEditorFrame import JsonEditorFrame
from TxDefi.UI.Components.LogsFrame import LogsFrame
from TxDefi.Utilities.SerializerUtil import StateSaverLoader
from TxDefi.Utilities.ThreadRunner import ThreadRunner  # Needed for Listbox
import TxDefi.Data.Globals as globals

class StrategyInfo:
    def __init__(self, ui_id, strategy_name: str, schema: dict, is_on: bool):
        self.strategy_name = strategy_name
        self.ui_id = ui_id
        self.settings = schema
        self.is_on = is_on
        self.strategy_id = None
     
class StrategiesFrame(ctk.CTkFrame, ThreadRunner, SwitchCallbackHandler):
    button_color = globals.sf_button_color
    header_color = globals.sf_header_color
    off_color = globals.sf_off_color
    on_color = globals.sf_on_color

    def __init__(self, master, trades_manager: TradesManager, **kwargs):
        super().__init__(master, **kwargs)
        ThreadRunner.__init__(self, 10)
        self.next_id = 0
        self.table_lock = threading.Lock()
        self.strategies : dict[int, StrategyInfo] = {} #key=ui id
        self.active_strategies_key_map : dict[str, int] = {} #key=strategy id
        self.strategy_factory = trades_manager.get_strategy_factory()
        self.selected_strategy : StrategyInfo = None
    
        # Configure 2 columns: left for names, right for split frames
        self.columnconfigure(0, weight=2) #Left panel
        self.columnconfigure(1, weight=7) #Center panel
        self.columnconfigure(2, weight=1) #Right panel
        self.rowconfigure(0, weight=1)
        self.trades_manager = trades_manager
        
        # Left pane with Listbox
        left_pane = ctk.CTkFrame(self, bg_color=self._bg_color)
        #left_pane.grid(row=0, column=0, sticky="nsew", padx=0, pady=10)
        left_pane.pack(side="left", fill="y")
        left_pane.rowconfigure(0, weight=9)
        left_pane.rowconfigure(1, weight=1)
  
        listbox = tk.Listbox(left_pane, font=("Calibri", 13), borderwidth=0, fg="white", bg=self._bg_color)
        listbox.bind("<Double-Button-1>", self.on_listbox_double_click)
        listbox.grid(row=0, sticky="nsew", padx=0, pady=0)

        buttons_pane = ctk.CTkFrame(left_pane, bg_color=self._bg_color)
        buttons_pane.grid(row=1, sticky="nsew", padx=0, pady=0)

        load_button = ctk.CTkButton(buttons_pane, text="Load", fg_color=self.button_color)
        load_button.bind("<Button-1>", lambda e: self.load())  
        load_button.pack(side=ctk.TOP, fill="both", expand=True, padx=0, pady=1)

        save_button = ctk.CTkButton(buttons_pane, text="Save", fg_color=self.button_color)
        save_button.bind("<Button-1>", lambda e: self.save())  
        save_button.pack(side=ctk.TOP, fill="both", expand=True, padx=0, pady=1)

        # Add names to the listbox
        strategy_names = self.strategy_factory.get_strategy_names()

        max_width = max(len(item) for item in strategy_names)
        for name in strategy_names:
            #name = name.center(max_width) #TODO center within parent frame
            listbox.insert(tk.END, name)

        #Center pane
        center_pane = ctk.CTkFrame(self, bg_color=self._bg_color, fg_color=self._fg_color)
        #center_pane.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        center_pane.pack(side="left", fill="y")
        center_pane.rowconfigure(0, weight=9)
        center_pane.rowconfigure(1, weight=1)
        center_pane.columnconfigure(0, weight=1)

        # Top half of right pane
        self.strategies_table = CustomCtkTable(center_pane, columns=self.create_header(True), bg_color = self._bg_color, fg_color="black")
        self.strategies_table.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.logs_pane = LogsFrame(center_pane)
        self.logs_pane.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        #Right pane
        self.edit_pane = JsonEditorFrame(self, bg_color = self._bg_color, fg_color=self._fg_color)
        self.edit_pane.pack(side="left", fill="both", expand=True)
        #self.edit_pane.grid(row=0, column=2, sticky="nsew", padx=0, pady=0)

        #Add thread runner callback for updating the strategies table
        self.add_callback(0, self.update_table)

    def save(self):
        json_list = []
        self.commit_edits()
        strategies = list(self.strategies.values())

        for strategy in strategies:
            json_list.append(strategy.settings)
        
        filepath = self.prompt_filepath(True)

        if filepath:
            state_saver = StateSaverLoader(filepath)
            state_saver.save_to_file(json_list)
        
    def load(self):  
        filepath = self.prompt_filepath(False)

        if filepath:
            self.clear_table()            
            state_loader = StateSaverLoader(filepath)

            json_data = state_loader.load_from_file()

            if isinstance(json_data, list):
                for item in json_data:
                    self.insert_row(item)
            else:
                self.insert_row(item)

    def clear_table(self):
        with self.table_lock:
            strategies = list(self.strategies.values())

            for strategy in strategies:
                self._delete_row(strategy.ui_id)

    def update_table(self): #TODO use a notification system instead of polling for state
        with self.table_lock:
            running_strategies = self.trades_manager.get_running_strategies()
            for strategy in running_strategies:
                state = strategy.get_state()
                strategy_id = strategy.get_id()
                ui_id = self.active_strategies_key_map.get(strategy_id)
               
                if ui_id is None:
                    #Must be a new trade
                    base_settings = strategy.schema()

                    current_settings = strategy.get_settings()

                    if current_settings:
                        base_settings.update(strategy.get_settings())

                    is_on = state != StrategyState.OFF and state != StrategyState.COMPLETE
                    
                    ui_id = self.insert_row(base_settings, is_on)
                    self.strategies[ui_id].strategy_id = strategy_id
                    self.active_strategies_key_map[strategy_id] = ui_id

                strategy_info = self.strategies.get(ui_id)            
              
                #Check for mismatches in running status
                if strategy_info and ((strategy_info.is_on and state != StrategyState.RUNNING) or (not strategy_info.is_on and state == StrategyState.RUNNING)):
                    self.strategies_table.update_item_column(ui_id, 4, None) # Update the toggle state column

                status_color = globals.sf_on_color if strategy_info.is_on else globals.sf_off_color

                self.strategies_table.update_item_column(ui_id, 2, state.name, fg_color = status_color) # Update the status column

                if self.selected_strategy and self.selected_strategy.strategy_id == strategy.get_id():
                    self.logs_pane.add_text(strategy.get_status())

    def handle_toggle_click(self, ui_id: int, toggled_on: bool):
        #Commit any edits before toggling on
        if toggled_on and self.selected_strategy and ui_id == self.selected_strategy.ui_id:
            self.commit_edits()

        strategy_info = self.strategies.get(ui_id)

        if strategy_info:
            strategy_info.is_on = toggled_on

            if strategy_info.strategy_id:
                self.trades_manager.toggle_strategy(strategy_info.strategy_id)
            else:
                strategy_ids = self.trades_manager.run_strategy_from_settings(strategy_info.settings)

                if strategy_ids and len(strategy_ids) > 0:
                    strategy_id = strategy_ids[0]
                    strategy_info.strategy_id = strategy_id
                    self.active_strategies_key_map[strategy_id] = ui_id

    def on_listbox_double_click(self, event):
        selection = event.widget.curselection()

        if selection:
            index = selection[0]
            value : str = event.widget.get(index)

            default_settings = self.strategy_factory.get_schema(value.strip())
            ui_id = self.insert_row(default_settings)
            strategy_info = self.strategies[ui_id]
            self.selected_strategy = strategy_info
            self.edit_pane.reset_form(strategy_info.settings)
           
    def insert_row(self, strategy_settings: dict, is_on = False)->int:
        strategy_name = strategy_settings.get("strategy_name")

        if strategy_name:
            ui_id = self.next_id
            strategy_info = StrategyInfo(ui_id, strategy_name, strategy_settings, is_on)

            row_items = self._create_row(strategy_info, True)

            self.strategies_table.insert_row(ui_id, row_items)

            self.strategies[ui_id] = strategy_info

            self.next_id += 1

            return ui_id

    def _delete_row(self, ui_id: int):
        strategy = self.strategies.get(ui_id)

        if strategy:
            if strategy.strategy_id: #TODO Ask are you sure?
                self.trades_manager.delete_strategy(strategy.strategy_id)

                if strategy.strategy_id in self.active_strategies_key_map:
                    self.active_strategies_key_map.pop(strategy.strategy_id)

            self.strategies_table.delete_row(ui_id)
            self.strategies.pop(ui_id)

            if self.selected_strategy == strategy:            
                self.edit_pane.clear()
                self.selected_strategy = None

    def commit_edits(self):
        #Save previous settings
        if self.selected_strategy:
            self.selected_strategy.settings = self.edit_pane.get_json()

    def _edit_row(self, ui_id: int):
        #Save previous settings
        self.commit_edits()
            
        selected_strategy = self.strategies.get(ui_id)

        if self.selected_strategy != selected_strategy:
            self.selected_strategy = selected_strategy
            self.logs_pane.clear()
            self.logs_pane.add_text(self.selected_strategy.strategy_name)
            self.edit_pane.reset_form(self.selected_strategy.settings)

    def _create_row(self, strategy_info: StrategyInfo, is_active: bool)->list:
        row_items: list[CtkTableCell] = []

        created_cell = CtkTableCell(self.strategies_table.scrollable_frame, bg_color = self._bg_color)
        created_cell.set_as_label(str(int(time.time())))
    
        name_cell = CtkTableCell(self.strategies_table.scrollable_frame, bg_color = self._bg_color)
        name_cell.set_as_label(strategy_info.strategy_name)

        edit_cell = CtkTableCell(self.strategies_table.scrollable_frame, bg_color = self._bg_color)
        edit_button = edit_cell.set_as_button("Edit", self.button_color)
        edit_button.bind("<Button-1>", lambda e: self._edit_row(strategy_info.ui_id)) 

        status_cell = CtkTableCell(self.strategies_table.scrollable_frame, bg_color = self.off_color, fg_color = self.off_color)
        status_cell.set_as_label("OFF")
 
        row_items = [created_cell, name_cell, status_cell, edit_cell]

        if is_active:
            toggle_button_cell = CtkTableCell(self.strategies_table.scrollable_frame, bg_color = self._bg_color)
            toggle_button_cell.set_as_toggle_button(strategy_info.ui_id, self, "On", "Off", self.button_color)    
            row_items.append(toggle_button_cell)
        
        delete_cell = CtkTableCell(self.strategies_table.scrollable_frame, bg_color = self._bg_color)
        delete_button = delete_cell.set_as_button("❌", self.button_color)
        delete_button.bind("<Button-1>", lambda e: self._delete_row(strategy_info.ui_id))      
        row_items.append(delete_cell)
        
        return row_items
    
    @staticmethod
    def create_header(is_active: bool)->dict:
        header = [{"header": "Created", "type": "string"}, 
                  {"header": "Name", "type": "string"},
                  {"header": "Status", "type": "string"},
                  {"header": "Edit", "type": "button"}]
        
        if is_active:
            header.append({"header": "Toggle", "type": "button"})

        header.append({"header": "", "type": "button"}) #delete button
        return header

    def prompt_filepath(self, is_save: bool):
        filetypes = [("JSON files", "*.json")]
        filextension = ".json"
        top = tk.Toplevel()
        top.withdraw()
        top.transient(self.master)

        if is_save:
            return filedialog.asksaveasfilename(
                parent=top, 
                defaultextension=filextension,
                filetypes=filetypes,
                title="Save JSON file"
            )
        else:
            return filedialog.askopenfilename(
                parent=top, 
                defaultextension=filextension,
                filetypes=filetypes,
                title="Loads JSON file"
            )