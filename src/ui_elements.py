# ui_elements.py
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from logic_loader import PairLoader
from logic_saver import AnnotationSaver
from ui_annotation import BoxHandler
from ui_annotation_displayer import AnnotationDisplayer


dataset_path = "/home/sarah/Documents/background_segmentation/small_relevant_sessions/store_b28cc24b-0dbf-483a-b9c6-d56367683935/session_0d428799-7b09-43b7-b352-e379c5f5abb7"
saving_path = "/home/sarah/Documents/change_detection/label-image-change"


class UIElements(tk.Frame):
    def __init__(self, root):
        super().__init__(root)

        self.loader = PairLoader(dataset_path)
        self.saver = AnnotationSaver(saving_path)
        self.handler = BoxHandler(self.loader, self.saver)
        self.displayer = AnnotationDisplayer()
        print(self.loader.image_pairs)

        # Subframes
        self.canvas_frame = CanvasFrame(self)
        self.nav_frame = NavigationFrame(self, 
                                         on_prev=self.prev_pair, 
                                         on_next=self.next_pair)
        self.ann_frame = AnnotationFrame(self, on_mark=self.mark_state,
                                         on_delete=self.delete_box, 
                                         on_reset=self.reset_pair)
        self.status = StatusFrame(self)

        # Layout
        self.canvas_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.nav_frame.grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.status.grid(row=1, column=1, sticky="e", padx=8, pady=6)
        self.ann_frame.grid(row=2, column=0, columnspan=2, pady=8)

        self.grid(row=0, column=0, sticky="nsew")

        self.refresh()

    def refresh(self):
        print("refreshing")
        pair = self.loader.current_pair()

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
        self.handler.selected_box_index = None
        self.handler.selected_canvas = None
        self.handler.selected_image = None

        self.status.update_status(self.loader.current_index, len(self.loader))

    def prev_pair(self):
        self.loader.prev_pair()
        self.refresh()

    def next_pair(self):
        self.loader.next_pair()
        self.refresh()

    # Annotation callbacks (wire to logic_saver later)
    def mark_state(self, state):
        pair = self.loader.current_pair()
        self.saver.save_pair(pair, state)
        if state == "annotated":
            self.handler = BoxHandler(pair, self.saver)
            # enable box drawing only when "Annotate" pressed
            self.canvas_frame.attach_boxes(self.handler, pair)

        print(f"Marked: {state}")
        self.refresh()

    def delete_box(self):
        """Delete the currently selected box safely."""
        try:
            self.handler.delete_box()
            self.refresh()
        except Exception as e:
            print(f"Delete failed: {e}")


    def reset_pair(self): print("Reset boxes")


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
            ("Unsure", lambda: on_mark("unsure")),
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
