import tkinter as tk
from tkinter import ttk

class LoadingOverlay:
    def __init__(self, parent):
        self.parent = parent
        self.overlay = None
        self.label = None

    def show(self):
        if self.overlay is None:
            self.overlay = tk.Toplevel(self.parent)
            self.overlay.transient(self.parent)
            self.overlay.grab_set()
            
            # Configure overlay window
            self.overlay.overrideredirect(True)
            self.overlay.configure(background='gray50')
            self.overlay.attributes('-alpha', 0.7)
            
            # Position and size overlay
            self.parent.update_idletasks()
            width = self.parent.winfo_width()
            height = self.parent.winfo_height()
            x = self.parent.winfo_x()
            y = self.parent.winfo_y()
            self.overlay.geometry(f"{width}x{height}+{x}+{y}")
            
            # Add loading label
            self.label = tk.Label(
                self.overlay,
                text="Loading...",
                font=('Helvetica', 14),
                background='gray50',
                foreground='white'
            )
            self.label.place(relx=0.5, rely=0.5, anchor='center')
            
            self.parent.update()

    def hide(self):
        if self.overlay is not None:
            self.overlay.destroy()
            self.overlay = None
            self.label = None
