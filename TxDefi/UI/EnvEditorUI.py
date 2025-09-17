from pydoc import text
from dotenv import dotenv_values
import customtkinter as ctk
import os
import sys

sys.path.insert(1, os.getcwd()) #needed to access resources outside this fold
from TxDefi.UI.Components.PasswordManagerUI import PasswordManagerUI
from TxDefi.Utilities.Encryption import SupportEncryption
from TxDefi.UI.Components.ScrollableFrame import ScrollableFrame
import TxDefi.Utilities.Encryption as encryption_util
import TxDefi.Utilities.FileUtil as fileutil
import TxDefi.Data.Globals as globals

class EnvEditorUI(ctk.CTkFrame):
    WALLET_ENCRYPTION_KEY = "WALLET_ENCRYPTION"
    env_file = ".env"
    def __init__(self, parent, appname: str, profile: str):
        super().__init__(parent)
        self.encryption = SupportEncryption.NONE
        self.data = EnvEditorUI.schema()
        self.entries : dict[str, ctk.CTkEntry] = {} # store entry widgets
        self.pass_gui = PasswordManagerUI(parent, appname, profile)
        self.env_path = f"{os.getcwd()}/{self.env_file}"
        self.build_ui()

    def build_ui(self):
        self.pack(padx=20, pady=10, fill="both", expand=True)
        ctk.CTkLabel(self, text=self.env_path, font=("Calibri", 12)).pack(side="top")

        scrollable_frame = ScrollableFrame(self)
        scrollable_frame.inner_frame.grid_columnconfigure(0, weight=1)
        scrollable_frame.inner_frame.grid_columnconfigure(1, weight=5)

        row = 0

        for key, item in self.data.items():
            label = ctk.CTkLabel(scrollable_frame.inner_frame, text=key, anchor="w")
            label.grid(row=row, column=0, sticky="w", padx=5, pady=5)

            entry = ctk.CTkEntry(scrollable_frame.inner_frame)
            entry.insert(0, str(item))
            entry.grid(row=row, column=1, sticky="ew", padx=5, pady=5)

            self.entries[key] = entry
            row += 1

        scrollable_frame.pack(fill="both", expand=True)
        # Load & Save buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(padx=5, pady=5)

        ctk.CTkButton(button_frame, text="Load", command=self.load_values).grid(row=0, column=0, padx=10)
        ctk.CTkButton(button_frame, text="Save", command=self.save_values).grid(row=0, column=1, padx=10)
        ctk.CTkButton(button_frame, text="Change Password", command=self.change_pwd).grid(row=0, column=2, padx=10)

    def change_pwd(self):
        self.pass_gui.show_window()
        self.save_values() #Doing this to encrypt keys with new pass

    def load_values(self):
        data = dotenv_values(self.env_file)
        
        if data:
            self.encryption = SupportEncryption.NONE
            pwd = None
            self.data = data

            for key, item in self.entries.items():
                new_value = data.get(key)

                if key == self.WALLET_ENCRYPTION_KEY:
                    self.encryption = SupportEncryption.to_enum(new_value)

                    if self.encryption is not SupportEncryption.NONE:
                        pwd = encryption_util.get_encryption_password(self.pass_gui.app_name, self.pass_gui.user_name)

                        if not pwd:
                            print(f"Cannot decrypt hash. No passord found for {self.pass_gui.app_name}:{self.pass_gui.user_name}.")
                elif key == "PAYER_HASH" and self.encryption != SupportEncryption.NONE:
                    if not pwd:
                        new_value = "<your key>"
                    else:
                        new_value = encryption_util.decrypt_wallet_key(new_value, pwd, self.encryption)

                if new_value:
                    item.delete(0, "end")
                    item.insert(0, new_value)
  
    def save_values(self):
        self.encryption = SupportEncryption.NONE
        pwd = None
        out_text = ""
        for key, item in self.entries.items():
            value : str = item.get()
            if key == self.WALLET_ENCRYPTION_KEY:
                self.encryption = SupportEncryption.to_enum(value)

                if self.encryption is not SupportEncryption.NONE:
                    pwd = encryption_util.get_encryption_password(self.pass_gui.app_name, self.pass_gui.user_name)

                    if not pwd:
                        pwd = self.pass_gui.prompt_password()
            elif key == "PAYER_HASH" and self.encryption != SupportEncryption.NONE:
                value = encryption_util.encrypt_wallet_key(bytes(value, "utf-8"), pwd, self.encryption)

            out_text += f"{key}={value}\n"

        #TODO Prompt are your sure?
        fileutil.write_file(self.env_file, out_text, 'w')            

    @staticmethod
    def schema()->dict:
        return {
            "MODE" : "SIM | REAL",
            "DEFAULT_SIM_SOL" : 100.17,
            EnvEditorUI.WALLET_ENCRYPTION_KEY : "NONE | AES",
            "CUSTOM_STRATEGIES_PATH" : "Examples/MyStrategies",
            "PAYER_HASH" : "<your wallet key>",
            "HTTP_RPC_URI" : "<your rpc node uri>",
            "WSS_RPC_URI" : "<your wss rpc node uri>",
            "JITO_URL" : "https://slc.mainnet.block-engine.jito.wtf/api/v1/bundles",
            "JITO_TIP_ADDRESS" : "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT",  
            "HTTP_RPC_URI" : "<your rpc node uri>",
            "TX_SUBS_WITH_GEYSER" : "True | False",
            "GEYSER_WSS" : "<your geyser uri with port number if applicable>",
            "BINANCE_API_KEY" : "<your key>",
            "BINANCE_API_SECRET" : "<your key>",
            "X_CONSUMER_KEY" : "<your key>",
            "X_CONSUMER_SECRET" : "<your key>",
            "X_BEARER_TOKEN" : "<your key>",
            "TELEGRAM_API_ID" : "<your key>",
            "TELEGRAM_API_HASH" : "<your key>",
            "TELEGRAM_CHANNEL_NAMES" : 'channel#1,channel#2',   
            "DISCORD_BOT_TOKEN" : "<your key>",
            "DISCORD_PUBLIC_KEY" : "<your key>",
            "DISCORD_CHANNEL_NAMES" : 'channel#1,channel#2',
            "IFTTT_WEBHOOK_NAME" : "ifttt-webhook",
            "IFTTT_WEBHOOK_PORT" : 5000,  
            "ANTHROPIC_API_KEY" : "<your key>",
            "MODEL" : "claude-3-5-sonnet-20241022",
            "RPC_RATE_LIMIT" : 50,
            "AUTO_BUY_IN_SOL" : .001,
            "DEFAULT_SLIPPAGE" : 50,
            "DEFAULT_PRIORITY_FEE" : 0.003
        } 
   
if __name__ == "__main__":
    test_data = EnvEditorUI.schema()
    app = EnvEditorUI(test_data)
    app.mainloop()
