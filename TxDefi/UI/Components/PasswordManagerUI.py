import json
import os
import sys

sys.path.insert(1, os.getcwd()) #needed to access resources outside this fold
import customtkinter as ctk

from TxDefi.UI.Components.CustomWindow import CustomWindow
from TxDefi.Utilities import Encryption

class PasswordManagerUI(CustomWindow):
    def __init__(self, parent, app_name: str, user_name: str):
        super().__init__(parent, "")

        self.app_name = app_name
        self.user_name = user_name

        pwd = Encryption.get_encryption_password(app_name, user_name)

        if pwd:
            enter_password_label = "New Password:"
        else:
            enter_password_label = "Password:"
        
        ctk.CTkLabel(self, text=enter_password_label).pack(pady=(5, 5))
        self.new_pwd = ctk.CTkEntry(self, show="*")
        self.new_pwd.pack()

        ctk.CTkLabel(self, text="Confirm Password:").pack(pady=(5, 5))
        self.confirm_pwd = ctk.CTkEntry(self, show="*")
        self.confirm_pwd.pack()

        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.pack(pady=1)

        ctk.CTkButton(self, text="Commit", command=self.change_password).pack(pady=2)

        self.geometry("300x300")    
        self.center_window(300, 300)

        self.after(200, lambda: self.resize_window(padx=20))

    def prompt_password(self)->str:
        pwd = Encryption.get_encryption_password(self.app_name, self.user_name)

        if pwd:
            return pwd
    
        self.show_window()
     
        return Encryption.get_encryption_password(self.app_name, self.user_name)
    
    def change_password(self):
        new = self.new_pwd.get()
        confirm = self.confirm_pwd.get()

        if not new or not confirm:
            self.status_label.configure(text="All fields are required.", text_color="red")
            return

        if new != confirm:
            self.status_label.configure(text="New passwords do not match.", text_color="red")
            return
        
        Encryption.set_password(self.app_name, self.user_name, new)

        self.status_label.configure(text="Password changed successfully!", text_color="green")
        self.destroy()

if __name__ == "__main__":
    # This is your existing encrypted key (simulate or load from file)
    wallet_key = b"my_secret_solana_private_key"
    initial_pwd = "oldpass123"
    #encrypted = encrypt_wallet_key(wallet_key, initial_pwd)

    app = PasswordManagerUI(None, "TxDefi", "Profile2")
    app.show_window()
    app.mainloop()

