import tkinter as tk
from tkinter import messagebox
import tkinter.simpledialog as sd

from src.ui.ui_elements import UIElements
from src.ui.ui_styles import init_ttk_styles
from src.logic_annotation.logic_data_handler import (
    UnsureDataHandler,
    InconsistentDataHandler,
)
from src.config import USERNAME


class UIReviewApp(tk.Tk):
    def __init__(self, batch_type="unsure", api_base="http://172.30.20.31:8081", user=USERNAME):
        super().__init__()
        init_ttk_styles(self)
        self.title(f"Review Mode – {batch_type.capitalize()}")
        self.minsize(800, 600)
        self.geometry("1200x800")

        user_filter = self.ask_user_filter(USERNAME)
        print("User selection:", user_filter)
        
        # Choose the right handler
        if batch_type == "unsure":
            handler = UnsureDataHandler(api_base=api_base, user=user, size=5)
        elif batch_type == "inconsistent":
            handler = InconsistentDataHandler(api_base=api_base, user=user, selected_users=user_filter, size=5)
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

    def ask_user_filter(self, default_user):
        import tkinter as tk

        ANNOTATOR_LIST = [
            "santiago",
            "almas",
            "niklas",
            "sarah",
        ]

        win = tk.Toplevel(self)
        win.title("Choose Annotators")
        win.geometry("350x320")
        win.grab_set()

        tk.Label(win, text="Select annotators to review:", font=("Arial", 12)).pack(pady=10)

        # --- Checkboxes ---
        vars_map = {}
        frame = tk.Frame(win)
        frame.pack(pady=5)

        for name in ANNOTATOR_LIST:
            var = tk.BooleanVar(value=(name == default_user))
            cb = tk.Checkbutton(frame, text=name, variable=var, anchor="w")
            cb.pack(fill="x", padx=20)
            vars_map[name] = var

        # Extra options
        chk_all = tk.BooleanVar(value=False)

        def on_check_all():
                state = chk_all.get()
                for var in vars_map.values():
                    var.set(state)

        tk.Checkbutton(
            win,
            text="Select all annotators",
            variable=chk_all,
            command=on_check_all,
            anchor="w"
        ).pack(fill="x", padx=20, pady=(10, 0))

        selected = {"value": None}

        def confirm():

            # Collect all selected names
            chosen = [name for name, var in vars_map.items() if var.get()]

            # If 'all' was selected, override list
            if chk_all.get():
                chosen = ANNOTATOR_LIST.copy()

            selected["value"] = chosen

            win.destroy()

        tk.Button(win, text="OK", command=confirm).pack(pady=15)

        self.wait_window(win)
        return selected["value"]



if __name__ == "__main__":
    # Choose review mode: "unsure" or "inconsistent"
    app = UIReviewApp(batch_type="inconsistent", api_base="http://172.30.20.31:8081", user=USERNAME)
    app.run()
