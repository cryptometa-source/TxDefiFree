from PIL import Image, ImageDraw, ImageFont
import customtkinter as ctk
from tkinter import filedialog

class ImageEditor:
    black = (0, 0, 0)
    white = (255, 255, 255)
    green = (18, 132, 18)
    red = (255, 0, 0)
    yellow = (181, 173, 81)
    gray = (159, 160, 159)
    def __init__(self, img_path: str):
        self.img_path = img_path
        self.edited_image = Image.open(img_path).convert("RGBA")
        self.draw = ImageDraw.Draw(self.edited_image)
    
    def undo_edits(self):
        self.edited_image = Image.open(self.img_path).convert("RGBA")
        self.draw = ImageDraw.Draw(self.edited_image)

    def add_text(self, text: str, xy_pos: tuple, font: ImageFont, color: set, center = False):
        if center:
            text_width = self.draw.textlength(text, font=font)
            xy_pos = (xy_pos[0]-text_width/2, xy_pos[1])

        self.draw.text(xy_pos, text, fill=color, font=font) 
        
    def get_edited_image(self)->Image:
        return self.edited_image

    def get_image_size(self)->tuple:
        return self.edited_image.size
    
    def save_as(self, filepath:str):
        self.edited_image.save(filepath)

if __name__ == "__main__":
    # Example usage
    app = ctk.CTk()

    img_path = "TxDefi/Resources/images/pnltemplate.jpg"
    image_editor = ImageEditor(img_path)
    font_path1 = "TxDefi/Resources/fonts/BlackOpsOne-Regular.ttf"
    font_path2 = "TxDefi/Resources/fonts/BebasNeue-Regular.ttf"

    center_x = 379

    symbol = "DOGE/SOL"
    font = ImageFont.truetype(font_path2, 60)
    image_editor.add_text(symbol, (center_x, 254), font, ImageEditor.yellow, True)

    #PNL %
    pnl = round(1730.05, 2)
    text = f"+{pnl}%"    
    font = ImageFont.truetype(font_path1, 90)
    image_editor.add_text(text, (center_x, 355), font, ImageEditor.green, True)

    #Profit SOL
    sol = round(.5952, 4)
    usd = 78.22
    text = f"+{sol} SOL (${usd})"
    font = ImageFont.truetype(font_path1, 36)
    image_editor.add_text(text, (center_x, 459), font, ImageEditor.green, True)

    #Invested SOL
    text = f"Invested"
    font = ImageFont.truetype(font_path1, 48)
    image_editor.add_text(text, (center_x, 539), font, ImageEditor.gray, True)

    sol = round(.2252, 4)
    usd = 4.22
    text = f"{sol} SOL (${usd})"
    font = ImageFont.truetype(font_path1, 36)
    image_editor.add_text(text, (center_x, 597), font, ImageEditor.gray, True)

    width, height = image_editor.get_image_size()

    app.geometry(f"{width+100}x{height+100}")
    frame = ctk.CTkFrame(app, width=width, height=height)
    frame.pack(padx=20, pady=20)

    # Convert to CTkImage
    ctk_img = ctk.CTkImage(light_image=image_editor.get_edited_image(), size=(width, height))  # Resize as needed
    image_label = ctk.CTkLabel(frame, image=ctk_img, text="")  # text="" removes the default label text
    image_label.pack(padx=10, pady=10)

    btn = ctk.CTkButton(frame, text="Take Screenshot", command=image_editor.save_as)
    btn.pack(pady=10)

    app.mainloop()
