# ui_elements.py
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from logic_data_handler import DataHandler
from logic_saver import AnnotationSaver
from ui_annotation import BoxHandler, Flickerer
from ui_annotation_displayer import AnnotationDisplayer
from config import DATASET_DIR

dataset_path = DATASET_DIR
saving_path = "/home/sarah/Documents/change_detection/label-image-change"


class UIElements(tk.Frame):
    def __init__(self, root):
        super().__init__(root)

        self.data_handler = DataHandler(dataset_path)

        self.saver = AnnotationSaver(self.data_handler.current_session_info().path)
        self.handler = BoxHandler(self.data_handler, self.saver, ui=self)
        self.displayer = AnnotationDisplayer()

        self.saver.set_on_change(self.refresh)

        # Subframes
        self.canvas_frame = CanvasFrame(self)
        self.nav_frame = NavigationFrame(self, 
                                         on_prev=self.prev_pair, 
                                         on_next=self.next_pair)
        self.ann_frame = AnnotationFrame(self, on_mark=self.mark_state,
                                         on_delete=self.delete_box, 
                                         on_reset=self.reset_pair)
        self.status = StatusFrame(self)


        self.flickerer = Flickerer(ui=self)


        root.bind("<space>", self.toggle_flicker)

        # Layout
        self.canvas_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.nav_frame.grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.status.grid(row=1, column=1, sticky="e", padx=8, pady=6)
        self.ann_frame.grid(row=2, column=0, columnspan=2, pady=8)

        self.grid(row=0, column=0, sticky="nsew")

        self.refresh()

    def refresh(self):
        print("refreshing")
        pair = self.data_handler.current_pair()

        root = self.winfo_toplevel()
        root.update_idletasks()
        root_w, root_h = root.winfo_width(), root.winfo_height()
        if root_w <= 1 or root_h <= 1:
            root_w, root_h = 1200, 800

        self.displayer.display_pair(
            self.canvas_frame.canvas_left,
            self.canvas_frame.canvas_right,
            pair,
            self.saver.annotations, # are read from the json
            max_w=root_w,
            max_h=root_h
        )
        if not getattr(self.handler, "_moving", False):
            self.handler.selected_box_index = None
            self.handler.selected_canvas = None
            self.handler.selected_image = None

        self.status.update_status(
            self.data_handler.pairs.pair_idx,
            len(self.data_handler.pairs)
        )



    def prev_pair(self):
        current = None
        if self.data_handler.has_prev_pair_global():
            # normal case: move back inside this session
            current = self.data_handler.prev_pair()
        else:
            print("Reached start of all sessions")
            return
        if not current.pair_annotation:
            total_pairs = len(self.data_handler.pairs)
            self.saver.save_pair(current, self.data_handler.current_session_info(), "no_annotation", total_pairs)
        self.refresh()


    def next_pair(self):
        current = None
        if self.data_handler.has_next_pair_global():
            # normal case: move inside this session
            current = self.data_handler.next_pair()
        else:
            print("Reached end of all sessions")
            return

        if not current.pair_annotation:
            total_pairs = len(self.data_handler.pairs)
            self.saver.save_pair(current, self.data_handler.current_session_info(), "no_annotation", total_pairs)
        self.refresh()


    # Annotation callbacks (wire to logic_saver later)
    def mark_state(self, state):
        pair = self.data_handler.current_pair()
        total_pairs = len(self.data_handler.pairs)
        self.saver.save_pair(pair, self.data_handler.current_session_info(), state, total_pairs)
        if state == "annotated":
            # enable box drawing only when "Annotate" pressed
            self.canvas_frame.attach_boxes(self.handler, pair)
        else: self.next_pair()

        print(f"Marked: {state}")

    def delete_box(self):
        """Delete the currently selected box safely."""
        try:
            self.handler.delete_box()
        except Exception as e:
            print(f"Delete failed: {e}")


    def reset_pair(self):
        pair = self.data_handler.current_pair()
        self.saver.reset_pair(pair)
        print("Reset boxes")


    
    def toggle_flicker(self, event=None):
        pair = self.data_handler.current_pair()

        root = self.winfo_toplevel()
        root.update_idletasks()
        root_w, root_h = root.winfo_width(), root.winfo_height()
        if root_w <= 1 or root_h <= 1:
            root_w, root_h = 1200, 800

        # toggle flicker on the right canvas
        self.flickerer.toggle_flicker(self.canvas_frame.canvas_right, pair, root_w // 2, root_h, interval=150)



class CanvasFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self._images = []

        self.canvas_left = tk.Canvas(self, bg="gray", highlightthickness=0)
        self.canvas_right = tk.Canvas(self, bg="gray", highlightthickness=0)
        self.canvas_left.grid(row=0, column=0, padx=10, pady=10)
        self.canvas_right.grid(row=0, column=1, padx=10, pady=10)

    def _scale_image(self, pil_img, max_w, max_h):
        w, h = pil_img.size
        scale = min(max_w / w, max_h / h)
        return pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)



    def attach_boxes(self, handler, pair):
        """Attach existing handler to canvases and redraw boxes."""
        handler.attach_to_canvas(self.canvas_left, pair.image1)
        handler.attach_to_canvas(self.canvas_right, pair.image2)
        self.parent.refresh()
        


class NavigationFrame(tk.Frame):
    def __init__(self, parent, on_prev, on_next):
        super().__init__(parent)
        ttk.Button(self, text="Prev", command=on_prev).grid(row=0, column=0)
        ttk.Button(self, text="Next", command=on_next).grid(row=0, column=1)


class AnnotationFrame(tk.Frame):
    def __init__(self, parent, on_mark, on_delete, on_reset):
        super().__init__(parent)
        annotation_frame = ttk.Frame(self)
        annotation_frame.grid(row=0, column=0, columnspan=2, pady=10)

        buttons = [
            ("Chaos", lambda: on_mark("chaos")),
            ("Nothing", lambda: on_mark("nothing")),
            ("Unsure", lambda: on_mark("no_annotation")),
            ("Annotate", lambda: on_mark("annotated")),
            ("Delete Box", on_delete),
            ("Reset", on_reset),
        ]

        for col, (text, cmd) in enumerate(buttons):
            ttk.Button(annotation_frame, text=text, command=cmd).grid(row=0, column=col, padx=5)


class StatusFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.label_info = ttk.Label(self, text="")
        self.label_info.grid(row=0, column=0, columnspan=2)

    def update_status(self, index, total):
        self.label_info.config(text=f"Pair {index+1}/{total}")
