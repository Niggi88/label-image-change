# ui_elements.py
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from src.logic_annotation.logic_data_handler import SessionDataHandler
from src.logic_annotation.logic_saver import AnnotationSaver
from src.ui.ui_annotation import BoxHandler, Flickerer, Crosshair
from src.ui.ui_annotation_displayer import AnnotationDisplayer
from src.config import DATASET_DIR
from tkinter import messagebox


dataset_path = DATASET_DIR
saving_path = "/home/sarah/Documents/change_detection/label-image-change"

from src.ui.ui_styles import *

class UIElements(tk.Frame):
    def __init__(self, root, data_handler=None, skip_completed=False):
        super().__init__(root)

        # Make root window resizable
        root.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)

        # Make this frame expand
        self.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)   # top frame (images) expands
        self.rowconfigure(1, weight=0)   # bottom frame (controls) fixed
        self.columnconfigure(0, weight=1)

        if data_handler is not None:
            self.data_handler = data_handler
        else:
            self.data_handler = SessionDataHandler(dataset_path, skip_completed=skip_completed)
        
        self.handler = BoxHandler(self.data_handler, self.data_handler.saver, ui=self)
        self.displayer = AnnotationDisplayer()
        self.data_handler.saver.set_on_change(self.refresh)
        self.flickerer = Flickerer(ui=self)

        # --- Subframes ---
        self.top_frame = tk.Frame(self)
        self.bottom_frame = tk.Frame(self)

        # Canvases (inside top_frame)
        self.canvas_frame = CanvasFrame(self.top_frame, parent_ui=self)

        # Controls (inside bottom_frame)
        self.nav_frame = NavigationFrame(self.bottom_frame,
                                         on_prev=self.prev_pair,
                                         on_next=self.next_pair)
        self.status = StatusFrame(self.bottom_frame)
        self.ann_frame = AnnotationFrame(self.bottom_frame,
                                         on_mark=self.mark_state,
                                         on_delete=self.delete_box,
                                         on_reset=self.reset_pair)

        # Bind keys
        root.bind("<space>", self.toggle_flicker)
        root.bind("<Configure>", self._on_resize)

        # --- Main layout: a 3x3 grid to center everything ---
        self.rowconfigure(0, weight=1)   # top spacer
        self.rowconfigure(1, weight=0)   # content row
        self.rowconfigure(2, weight=1)   # bottom spacer
        self.columnconfigure(0, weight=1)  # left spacer
        self.columnconfigure(1, weight=0)  # content col
        self.columnconfigure(2, weight=1)  # right spacer

        self.top_bar = tk.Frame(self)
        self.top_bar.grid(row=0, column=0, columnspan=3, sticky="ew")

        self.session_frame = SessionFrame(self.top_bar)
        self.session_frame.pack(side="left", padx=10, pady=10)


        if getattr(self.data_handler, "mode", None) == "annotation":
            self.skip_button = ttk.Button(self.top_bar, text="Skip Session", style=STYLE_SKIP,
                                        command=self.skip_session)
            self.skip_button.pack(side="right", padx=10, pady=10)


        # --- Content frame (centered) ---
        self.content_frame = tk.Frame(self)
        self.content_frame.grid(row=1, column=1)


        # Canvases (images)
        self.canvas_frame = CanvasFrame(self.content_frame, parent_ui=self)
        self.canvas_frame.grid(row=0, column=0, sticky="n")

        # Annotation buttons
        self.ann_frame = AnnotationFrame(self.content_frame,
                                        on_mark=self.mark_state,
                                        on_delete=self.delete_box,
                                        on_reset=self.reset_pair)
        
        self.ann_frame.grid(row=1, column=0, columnspan=2, pady=(30, 5))  

        # Navigation bar
        self.nav_bar = tk.Frame(self.content_frame)
        self.nav_bar.grid(row=2, column=0, columnspan=2, pady=(10, 20))

        self.prev_btn = ttk.Button(self.nav_bar, text="Prev", style=STYLE_NAV, command=self.prev_pair)
        self.prev_btn.pack(side="left", padx=30, pady=15)

        self.status = StatusFrame(self.nav_bar)
        self.status.pack(side="left", padx=10)

        self.next_btn = ttk.Button(self.nav_bar, text="Next", style=STYLE_NAV, command=self.next_pair)
        self.next_btn.pack(side="left", padx=30, pady=15)


        # --- Keyboard Shortcuts ---
        root.bind("a", lambda e: self.mark_state("annotated"))   # A = Annotate
        root.bind("n", lambda e: self.mark_state("nothing"))     # N = Nothing
        root.bind("c", lambda e: self.mark_state("chaos"))       # C = Chaos
        root.bind("u", lambda e: self.mark_state("no_annotation")) # U = Unsure/No Annotation
        root.bind("d", lambda e: self.delete_box())              # D = Delete selected box
        root.bind("x", lambda e: self.reset_pair())              # X = Reset pair
        root.bind("f", lambda e: self.next_pair())               # F = Next pair
        root.bind("s", lambda e: self.prev_pair())               # S = Previous pair


        self.refresh()



    def _on_resize(self, event=None):
        # cancel pending refresh if still waiting
        if hasattr(self, "_resize_job") and self._resize_job:
            self.after_cancel(self._resize_job)

        # schedule refresh shortly after resizing finished
        self._resize_job = self.after(200, self._refresh_after_resize)

    def _refresh_after_resize(self):
        self._resize_job = None
        self.refresh()
            
    def refresh(self):
        print("refreshing")
        pair = self.data_handler.current_pair()

        root = self.winfo_toplevel()
        root.update_idletasks()
        root_w, root_h = root.winfo_width(), root.winfo_height()
        if root_w <= 1 or root_h <= 1:
            root_w, root_h = 1200, 800

        ann_all = self.data_handler.saver.annotations
        ann_lookup = ann_all.get("items", ann_all)

        self.displayer.display_pair(
            self.canvas_frame.canvas_left,
            self.canvas_frame.canvas_right,
            pair,
            ann_lookup,
            max_w=root_w,
            max_h=root_h
        )
        if not getattr(self.handler, "_moving", False):
            self.handler.selected_box_index = None
            self.handler.selected_canvas = None
            self.handler.selected_image = None


        self.status.update_text(self.data_handler.get_status_text())
        self.session_frame.update_text(self.data_handler.get_session_text())

        self.canvas_frame.canvas_right.focus_set()



    def prev_pair(self):
        old_info = self.data_handler.context_info()

        if self.data_handler.has_prev_pair_global():
            current = self.data_handler.prev_pair()
        else:
            messagebox.showinfo("Start Reached", "You have reached the start.")
            return

        # save default if necessary
        pid = str(current.pair_id)
        ann_all = self.data_handler.saver.annotations
        entry = ann_all.get("items", {}).get(pid) if "items" in ann_all else ann_all.get(pid)

        if not entry or "pair_state" not in entry:
            self.data_handler.saver.save_pair(
                current,
                "no_annotation",
                self.data_handler.context_info(),
            )

        self.refresh()

        # detect transition
        new_info = self.data_handler.context_info()
        if new_info["progress"]["label"] != old_info["progress"]["label"]:
            messagebox.showinfo("Previous", f"Moving back to previous session")


    def next_pair(self):
        old_info = self.data_handler.context_info()

        if self.data_handler.has_next_pair_global():
            current = self.data_handler.next_pair()
        else:
            if self.data_handler.mode == "review":
                self._ask_upload_batch()
            else:
                messagebox.showinfo("End Reached", "You have reached the end.")
            return
        
        # save default if necessary
        pid = str(current.pair_id)
        ann_all = self.data_handler.saver.annotations
        entry = ann_all.get("items", {}).get(pid) if "items" in ann_all else ann_all.get(pid)

        if not entry or "pair_state" not in entry:
            self.data_handler.saver.save_pair(
                current,
                "no_annotation",
                self.data_handler.context_info(),
            )

        self.refresh()

        # detect transition
        new_info = self.data_handler.context_info()
        if new_info["progress"]["label"] != old_info["progress"]["label"]:
            messagebox.showinfo("Next", f"Moving on to next session.")


    def _ask_upload_batch(self):
        confirm = messagebox.askyesno(
            "Batch finished",
            "You have reached the end of this batch.\n\nDo you want to upload your results now?"
        )
        if confirm:
            try:
                # upload results via data_handler
                results = self.data_handler.saver.annotations
                resp = self.data_handler.upload_results(results)

                messagebox.showinfo("Upload complete", "Batch has been uploaded and marked completed.")

                # Load a fresh batch after completion
                self.data_handler.load_current_pairs()
                self.refresh()

            except Exception as e:
                messagebox.showerror("Upload failed", f"Something went wrong:\n{e}")


    # Annotation callbacks (wire to logic_saver later)
    def mark_state(self, state):
        pair = self.data_handler.current_pair()
        total_pairs = len(self.data_handler.pairs)
        self.data_handler.saver.save_pair(pair, state, self.data_handler.context_info())
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
        ctx = self.data_handler.context_info()
        self.data_handler.saver.reset_pair(pair, ctx)
        print("Reset boxes")


    def skip_session(self):
        confirm = messagebox.askyesno("Skip Session", "Do you really want to skip this session?")
        if not confirm:
            return  # user canceled

        self.data_handler.skip_current_session()
        messagebox.showinfo("Session Skipped", "This session was skipped. Next session will start now.")
        self.refresh()

    
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
    def __init__(self, master, parent_ui):
        super().__init__(master)
        self.parent_ui = parent_ui
        self._images = []

               # Make two equal columns that expand
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.canvas_left = tk.Canvas(self, bg="gray", highlightthickness=0)
        self.canvas_right = tk.Canvas(self, bg="gray", highlightthickness=0)

        # Important: sticky="nsew" lets canvases stretch fully
        self.canvas_left.grid(row=0, column=0)
        self.canvas_right.grid(row=0, column=1)

        self.crosshair_left = Crosshair(self.canvas_left)
        self.crosshair_right = Crosshair(self.canvas_right)


    def _scale_image(self, pil_img, max_w, max_h):
        w, h = pil_img.size
        scale = min(max_w / w, max_h / h)
        return pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)



    def attach_boxes(self, handler, pair):
        """Attach existing handler to canvases and redraw boxes."""
        handler.attach_to_canvas(self.canvas_left, pair.image1)
        handler.attach_to_canvas(self.canvas_right, pair.image2)
        self.parent_ui.refresh()
        


class NavigationFrame(tk.Frame):
    def __init__(self, parent, on_prev, on_next):
        super().__init__(parent)
        ttk.Button(self, text="Prev", command=on_prev).grid(row=0, column=0)
        ttk.Button(self, text="Next", command=on_next).grid(row=0, column=1)


class AnnotationFrame(tk.Frame):
    def __init__(self, parent, on_mark, on_delete, on_reset):
        super().__init__(parent)

        buttons = [
            ("Nothing Changed", lambda: on_mark("nothing")),
            ("Chaos", lambda: on_mark("chaos")),
            ("Unsure", lambda: on_mark("no_annotation")),
            ("Annotate", lambda: on_mark("annotate")),
            ("Delete Selected Box", on_delete),
            ("Reset", on_reset),
        ]

        for col, (text, cmd, style) in enumerate([
            ("Nothing Changed", lambda: on_mark("nothing"), STYLE_NOTHING),
            ("Chaos", lambda: on_mark("chaos"), STYLE_CHAOS),
            ("Unsure", lambda: on_mark("no_annotation"), STYLE_UNSURE),
            ("Annotate", lambda: on_mark("annotated"), STYLE_ANNOTATE),
            ("Delete Selected Box", on_delete, STYLE_DELETE),
            ("Reset", on_reset, STYLE_RESET),
        ]):
            btn = ttk.Button(self, text=text, command=cmd, style=style)
            btn.grid(row=0, column=col,
                    padx=BUTTON_PADX, pady=BUTTON_PADY,
                    sticky="nsew", ipady=BUTTON_IPADY)
            self.columnconfigure(col, weight=1)

        # Außenabstand für gesamte Leiste
        self.grid(sticky="ew", padx=OUTER_PADX)


class SessionFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.label_info = ttk.Label(self, text="", anchor="w", style=STYLE_SESSION)
        self.label_info.pack()

    def update_text(self, text):
        self.label_info.config(text=text)


class StatusFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.label_info = ttk.Label(self, text="", style=STYLE_STATUS)
        self.label_info.pack()

    def update_text(self, text):
        self.label_info.config(text=text)
