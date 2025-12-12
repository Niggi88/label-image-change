import tkinter as tk
from tkinter import messagebox
import tkinter.simpledialog as sd
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.ui.ui_elements import UIElements
from src.ui.ui_styles import init_ttk_styles
from src.logic_annotation.logic_data_handler import (
    UnsureDataHandler,
    InconsistentDataHandler,
)
from src.config import USERNAME
from src.ui.ui_initial_checkbox import Checkbox


class UIReviewApp(tk.Tk):
    def __init__(self, batch_type="unsure", api_base="http://172.30.20.31:8081", user=USERNAME):
        super().__init__()
        init_ttk_styles(self)
        self.title(f"Review Mode – {batch_type.capitalize()}")
        self.minsize(800, 600)
        self.geometry("1200x800")

        self.checkbox = Checkbox(USERNAME)

        selection = self.checkbox.ask_user_filter(USERNAME)
        
        selected_users = selection.get("annotators")
        selected_model = selection.get("model")
        selected_batch_size = selection.get("batch_size")

        print("User selection:", selected_users)
        print("selected model: ", selected_model)
        print("selected batch size: ", selected_batch_size)

        # Choose the right handler
        if batch_type == "unsure":
            handler = UnsureDataHandler(api_base=api_base, user=user, size=5)
        elif batch_type == "inconsistent":
            handler = InconsistentDataHandler(api_base=api_base, user=user, selected_users=selected_users, size=5)
        else:
            raise ValueError("batch_type must be 'unsure' or 'inconsistent'")

        # Main UI
        self.ui_elements = UIElements(self, data_handler=handler)
        self.ui_elements.grid(row=0, column=0, sticky="nsew")

        # Allow resizing
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.handler = handler  # keep reference

    def run(self):
        self.mainloop()

    def upload_results(self):
        """Collect results and push back to API."""
        results = {
            f"{it['store_session_path']}|{it['pair_id']}": {
                "decision": "keep",  # FIXME: adjust logic / button mapping
                "reviewed_by": "sarah",
            }
            for it in self.handler.pairs
        }
        self.handler.upload_results(results)
        print("Results uploaded.")



if __name__ == "__main__":
    # Choose review mode: "unsure" or "inconsistent"
    app = UIReviewApp(batch_type="inconsistent", api_base="http://172.30.20.31:8081", user=USERNAME)
    app.run()
