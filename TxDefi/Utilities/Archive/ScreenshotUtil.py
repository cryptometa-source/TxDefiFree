import pyautogui
import time

def screenshot_widget(widget, filename="screenshot.png"):
    widget.update()  # Ensure geometry is up to date
    x = widget.winfo_rootx()
    y = widget.winfo_rooty()
    w = widget.winfo_width()
    h = widget.winfo_height()
    time.sleep(0.2)  # Give it a moment to draw
    screenshot = pyautogui.screenshot(region=(x, y, w, h))
    screenshot.save(filename)
    print(f"Saved screenshot to {filename}")