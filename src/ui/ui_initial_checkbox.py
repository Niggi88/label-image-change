import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import tkinter.simpledialog as sd

class Checkbox:
    def __init__(self, default_user):
        self.default_user = default_user
        self.annotator_list = [
            "santiago",
            "almas",
            "niklas",
            "sarah",
        ]

        self.model_list = ["main_real_data_large_xl-images_v1_20251215_133019", "real_data_v9_medium_santionly_20251127_181108", "main_real_data_large_xl-images_v1_1_3cl_datasets-v1-1"]


    def _build_annotator_checkboxes(self, parent, default_user):
        vars_map = {}

        tk.Label(parent, text="Select annotators:", font=("Arial", 12)).pack(pady=10)

        frame = tk.Frame(parent)
        frame.pack()

        for name in self.annotator_list:
            var = tk.BooleanVar(value=(name == default_user))
            cb = tk.Checkbutton(frame, text=name, variable=var, anchor="w")
            cb.pack(fill="x", padx=20)
            vars_map[name] = var

        return vars_map
    


    def _build_select_all_checkbox(self, parent, vars_map):
        chk_all = tk.BooleanVar(value=False)

        def on_check_all():
            state = chk_all.get()
            for var in vars_map.values():
                var.set(state)

        tk.Checkbutton(
            parent,
            text="Select all annotators",
            variable=chk_all,
            command=on_check_all
        ).pack(fill="x", padx=20, pady=(10, 0))

        return chk_all

    def _build_model_dropdown(self, parent):
        tk.Label(parent, text="Choose model:", font=("Arial", 12)).pack(pady=(20, 5))

        model_var = tk.StringVar(value=self.model_list[0])
        dropdown = ttk.Combobox(parent, textvariable=model_var, values=self.model_list, state="readonly")
        dropdown.pack()

        return model_var
    

    def _build_batchsize_selector(self, parent):
        tk.Label(parent, text="Batch size:", font=("Arial", 12)).pack(pady=(20, 5))

        batch_var = tk.StringVar(value="5")

        entry = tk.Entry(parent, textvariable=batch_var, width=10)
        entry.pack()

        return batch_var


    def ask_user_filter(self, default_user):

        win = tk.Toplevel()
        win.title("Choose Annotators / Model / Batchsize")
        win.geometry("380x420")
        win.grab_set()

        # Section 1: Checkboxes
        vars_map = self._build_annotator_checkboxes(win, default_user)

        # Section 1b: Select all
        chk_all = self._build_select_all_checkbox(win, vars_map)

        # Section 2: Model chooser
        model_var = self._build_model_dropdown(win)

        # Section 3: Batchsize
        batch_var = self._build_batchsize_selector(win)

        selected = {"value": None}

        def confirm():
            # Annotators
            chosen = [name for name, var in vars_map.items() if var.get()]
            if chk_all.get():
                chosen = self.annotator_list.copy()

            selected["value"] = {
                "annotators": chosen,
                "model": model_var.get(),
                "batch_size": batch_var.get(),
            }

            win.destroy()

        tk.Button(win, text="OK", command=confirm).pack(pady=20)

        win.wait_window()
        return selected["value"]