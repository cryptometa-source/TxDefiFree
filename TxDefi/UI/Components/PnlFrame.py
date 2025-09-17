import webbrowser
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from PIL import ImageFont
from TxDefi.Data.Amount import Amount
from TxDefi.Data.MarketDTOs import ProfitLoss
from TxDefi.Utilities.ImageEditor import ImageEditor
import TxDefi.Data.Globals as globals
     
class PnlFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.image_editor = ImageEditor(globals.pnl_image_path)
            
        self.image_label = ctk.CTkLabel(self, text="")  # text="" removes the default label text
        self.image_label.pack(padx=10, pady=10)

        button_frame = ctk.CTkFrame(self, **kwargs)
        button_frame.pack(side="right", padx=20, pady=20)
        btn = ctk.CTkButton(button_frame, text="Save Screenshot", command=self.save_as)
        btn.pack(side="left", padx=5, pady=10)
        btn = ctk.CTkButton(button_frame, text="See Transaction", command=self.open_uri)
        btn.pack(side="left", padx=5, pady=10)  
        self.click_uri = ""

    def save_as(self):
        top = tk.Toplevel()
        top.withdraw()
        top.transient(self.master)

        filetypes = [("PNG files", "*.png")]
        filextension = ".png"

        path = filedialog.asksaveasfilename(
                parent=self.master, 
                defaultextension=filextension,
                filetypes=filetypes,
                title="Save PNG file"
        )
        
        if path:
            self.image_editor.save_as(path)

    def open_uri(self):
        webbrowser.open(self.click_uri)

    def set_image(self, tx_uri: str, symbol: str, pnl_obj: ProfitLoss, quote_usd_price: Amount):
        self.image_editor.undo_edits()
        center_x = 379
        self.click_uri = tx_uri

        font = ImageFont.truetype(globals.bebas_font_path, 60)
        self.image_editor.add_text(symbol, (center_x, 254), font, ImageEditor.yellow, True)

        #PNL %
        pnl_percent_str = pnl_obj.pnl_percent.to_string(2)
        usd_pnl = round(pnl_obj.pnl.to_ui()*quote_usd_price.to_ui(), 2)
        pnl_str = pnl_obj.pnl.to_string(4)

        if pnl_obj.pnl_percent.to_ui() >= 0:
            color = ImageEditor.green

            if pnl_obj.pnl_percent.to_ui() > 0:
                pnl_percent_str = "+" + pnl_percent_str
        elif pnl_obj.pnl_percent.to_ui() == 0:
            color = ImageEditor.gray
        else:
            color = ImageEditor.red
            usd_pnl = abs(usd_pnl)
      
        text = f"{pnl_percent_str}%"    
        font = ImageFont.truetype(globals.blackops_font_path, 90)
        self.image_editor.add_text(text, (center_x, 355), font, color, True)

        #Profit SOL
        text = f"{pnl_str} SOL (${usd_pnl})"
        font = ImageFont.truetype(globals.blackops_font_path, 36)
        self.image_editor.add_text(text, (center_x, 459), font, color, True)

        #Invested SOL
        text = f"Invested"
        font = ImageFont.truetype(globals.blackops_font_path, 48)
        self.image_editor.add_text(text, (center_x, 539), font, ImageEditor.gray, True)

        invested_sol = pnl_obj.cost_basis.to_string(4)
        usd = round(pnl_obj.cost_basis.to_ui()*quote_usd_price.to_ui(), 2)
        text = f"{invested_sol} SOL (${usd})"
        font = ImageFont.truetype(globals.blackops_font_path, 36)
        self.image_editor.add_text(text, (center_x, 597), font, ImageEditor.gray, True)
        
        # Convert to CTkImage
        ctk_img = ctk.CTkImage(light_image=self.image_editor.get_edited_image(), size=self.image_editor.get_image_size()) # Resize as needed
        self.image_label.configure(image=ctk_img)
