from abc import abstractmethod
import customtkinter as ctk

class SwitchCallbackHandler:
    @abstractmethod
    def handle_toggle_click(self, ui_id, toggled_on: bool): #TODO could use an event instead of the button text, but this works for now
        print(f"Toggle: {self.id} {toggled_on}")

class ToggleButton(ctk.CTkButton):
    def __init__(self, master, ui_id: int, callback_handler: SwitchCallbackHandler, text_on="On", text_off="Off", **kwargs):
        super().__init__(master, **kwargs)
        self.text_on = text_on
        self.text_off = text_off
        self.state = False  # Starts in 'off' state
        self.ui_id = ui_id
        self.callback_handler = callback_handler
        self.configure(text=self.text_off, command=self.toggle)

    def set(self, state: bool):
        self.state = state
        new_text = self.text_on if self.state else self.text_off

        self.callback_handler.handle_toggle_click(self.ui_id, self.state)
        self.configure(text=new_text)

    def toggle(self):
        self.state = not self.state
        self.set(self.state)