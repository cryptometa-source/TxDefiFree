import customtkinter as ctk
import TxDefi.UI.Components.GuiHelperFunctions as gui_functions
import tomllib 

def load_app_info(toml_path="pyproject.toml")->dict:
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
    # Adjust the path depending on your toml structure
    app_info = data.get("project", {})
    return {
        "name": app_info.get("name", "Unknown App"),
        "description": app_info.get("description", ""),
        "version": app_info.get("version", "0.0.0"),
        "website": app_info.get("website", "https://example.com"),
        "discord": app_info.get("discord", "https://example.com")
    }

class AboutFrame(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
    
        app_info = load_app_info()
        # Title / info
        label = ctk.CTkLabel(self, text=f"{app_info['name'].upper()} v{app_info['version']}\n{app_info['description']}", font=("Arial", 16))
        label.pack(pady=(20, 10))

        # Clickable website link
        website_uri = f"{app_info['website']}"
        website_link = gui_functions.create_url_label(self, website_uri, website_uri)
        website_link.pack(pady=1)

        discord_uri = f"{app_info['discord']}"
        discord_link = gui_functions.create_url_label(self, discord_uri, discord_uri)
        discord_link.pack(pady=1) 

    def _close_parent(self):
        # If placed in a CTkToplevel, close it
        if isinstance(self.master, ctk.CTkToplevel):
            self.master.destroy()


# Example usage
def open_about_window():
    about_window = ctk.CTkToplevel()
    about_window.title("About")
    about_window.geometry("300x200")
    about_frame = AboutFrame(about_window)
    about_frame.pack(expand=True, fill="both")
