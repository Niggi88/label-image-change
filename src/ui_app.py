import tkinter as tk
from tkinter import ttk

from ui_elements import UIElements
from ui_styles import init_ttk_styles


'''
ui app
initialize root for window (entry point)
used to be: PairViewerApp
'''



class UIApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # Root window
        init_ttk_styles(self)
        self.title("Annotation Tool")
        self.geometry("1200x800")
        self.minsize(800, 600)      # don’t allow too tiny

        # Fenster-Gitter aufteilen
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Haupt-UI
        self.ui_elements = UIElements(self)
        self.ui_elements.grid(row=0, column=0, sticky="nsew")


    def run(self):
        """Start Tkinter main loop"""
        self.mainloop()


if __name__ == "__main__":
    app = UIApp()
    app.run()
