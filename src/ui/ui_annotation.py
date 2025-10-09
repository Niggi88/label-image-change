import uuid
from src.ui.ui_annotation_displayer import AnnotationDisplayer
import tkinter as tk

class BoxHandler:
    def __init__(self, data_handler, saver, ui=None):
        self.ui = ui

        self.data_handler = data_handler
        self.displayer = AnnotationDisplayer()

        self.start_x = None
        self.start_y = None
        self.current_rect = None

        self.selected_box_index = None
        self.selected_canvas = None
        self.selected_image = None
        self._drawing = False

        self._moving = False

    def attach_to_canvas(self, canvas, image):
        """
        Bind drawing events for the given canvas and AnnotatableImage.
        """
        canvas.bind("<Button-1>", lambda e: self.start_action(e, canvas, image))
        canvas.bind("<B1-Motion>", lambda e: self.draw_box(e, canvas))
        canvas.bind("<ButtonRelease-1>", lambda e: self.end_box(e, canvas, image))

        # new bindings for moving with right click
        canvas.bind("<Button-3>", lambda e: self.start_move(e, canvas, image))
        canvas.bind("<B3-Motion>", lambda e: self.move_box(e, canvas))
        canvas.bind("<ButtonRelease-3>", lambda e: self.end_move(e))

    def start_action(self, event, canvas, annot_img):
        """Entry point: decides if this is a selection or a new box draw."""
        scale_x = annot_img.img_size[0] / canvas.winfo_width()
        scale_y = annot_img.img_size[1] / canvas.winfo_height()
        x = int(event.x * scale_x)
        y = int(event.y * scale_y)

        # check if click is inside an existing box
        for i, b in enumerate(annot_img.boxes):
            if b["x1"] <= x <= b["x2"] and b["y1"] <= y <= b["y2"]:
                self.select_box(i, canvas, annot_img)
                self._drawing = False
                return

        # otherwise start drawing
        self.start_box(event, canvas)
        self._drawing = True


    def select_box(self, index, canvas, annot_img):
        """Mark box at given index as selected and redraw with highlight."""
        self.selected_box_index = index
        self.selected_canvas = canvas
        self.selected_image = annot_img
        print(f"Selected box {index} on image_id={annot_img.image_id}")
        # self.display_boxes(canvas, annot_img.boxes, highlight=index)


    def start_box(self, event, canvas):
        """Prepare to draw a new box."""
        self.start_x, self.start_y = event.x, event.y
        self.current_rect = None

    def draw_box(self, event, canvas):
        if not getattr(self, "_drawing", False):
            return

        # Clamp to canvas boundaries
        w, h = canvas.winfo_width(), canvas.winfo_height()
        x = max(0, min(event.x, w))
        y = max(0, min(event.y, h))

        # Delete old preview
        canvas.delete("preview")
        # Draw new preview
        self.current_rect = canvas.create_rectangle(
            self.start_x, self.start_y, x, y,
            outline="red", width=2, dash=(2, 2), tags="preview"
        )

    
    def end_box(self, event, canvas, annot_img):
        if self.start_x is None or not getattr(self, "_drawing", False):
            return
        self._drawing = False

        # Clamp release point to canvas boundaries
        w, h = canvas.winfo_width(), canvas.winfo_height()
        x2 = max(0, min(event.x, w))
        y2 = max(0, min(event.y, h))

        x1, y1 = self.start_x, self.start_y
        self.start_x = self.start_y = None

        # Ignore tiny boxes
        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
            canvas.delete("preview")
            self.current_rect = None
            return

        # Scale to image coordinates
        img_w, img_h = annot_img.img_size
        scale_x = img_w / canvas.winfo_width()
        scale_y = img_h / canvas.winfo_height()

        box = {
            "x1": max(0, min(img_w, int(min(x1, x2) * scale_x))),
            "y1": max(0, min(img_h, int(min(y1, y2) * scale_y))),
            "x2": max(0, min(img_w, int(max(x1, x2) * scale_x))),
            "y2": max(0, min(img_h, int(max(y1, y2) * scale_y))),
            "annotation_type": "item_removed" if annot_img.image_id == 1 else "item_added",
            "box_id": str(uuid.uuid4()),
        }

        annot_img.boxes.append(box)
        pair = self.data_handler.current_pair()
        ctx = self.data_handler.context_info()
        self.data_handler.saver.save_box(pair, box, ctx, state="annotated")

        # Cleanup preview
        canvas.delete("preview")
        self.current_rect = None
        if self.ui:
            self.ui.refresh()

    def delete_box(self):
        """Delete the currently selected box and update JSON."""
        if self.selected_box_index is None or self.selected_image is None:
            print("No box selected to delete")
            return

        # remove from memory
        removed_box = self.selected_image.boxes.pop(self.selected_box_index)
        print(f"Deleted box: {removed_box}")

        # redraw remaining boxes
        # self.display_boxes(self.selected_canvas, self.selected_image.boxes)

        # update annotations.json (remove box by pair_id)
        pair = self.data_handler.current_pair()
        ctx = self.data_handler.context_info()
        self.data_handler.saver.save_delete_box(pair, removed_box["box_id"], ctx)


        # reset selection
        self.selected_box_index = None
        self.selected_canvas = None
        self.selected_image = None

     # ---------------- MOVE ----------------

    def start_move(self, event, canvas, annot_img):
        """Starte das Verschieben einer Box (rechte Maustaste)."""
        scale_x = annot_img.img_size[0] / canvas.winfo_width()
        scale_y = annot_img.img_size[1] / canvas.winfo_height()
        x = int(event.x * scale_x)
        y = int(event.y * scale_y)

        for i, b in enumerate(annot_img.boxes):
            if b["x1"] <= x <= b["x2"] and b["y1"] <= y <= b["y2"]:
                self.selected_canvas = canvas
                self.selected_image = annot_img
                self._moving = True
                self._move_start_x, self._move_start_y = event.x, event.y
                self._moving_box = dict(b)
                self._moving_index = i

                # Temporäres Rechteck zeichnen
                img_w, img_h = annot_img.img_size
                scale_x_c = canvas.winfo_width() / img_w
                scale_y_c = canvas.winfo_height() / img_h
                self._moving_box_id = canvas.create_rectangle(
                    b["x1"] * scale_x_c,
                    b["y1"] * scale_y_c,
                    b["x2"] * scale_x_c,
                    b["y2"] * scale_y_c,
                    outline="red", width=2, dash=(3, 3), tags="moving_box"
                )

                # Box temporär aus Speicher entfernen (nicht redrawen!)
                annot_img.boxes.pop(i)
                return


    def move_box(self, event, canvas):
        """Bewege die aktuell gezogene Box – aktualisiere nur deren Koordinaten."""
        if not self._moving or not hasattr(self, "_moving_box_id"):
            return

        dx = event.x - self._move_start_x
        dy = event.y - self._move_start_y
        self._move_start_x, self._move_start_y = event.x, event.y

        coords = canvas.coords(self._moving_box_id)
        new_coords = [
            coords[0] + dx,
            coords[1] + dy,
            coords[2] + dx,
            coords[3] + dy,
        ]

        # Begrenze auf Canvas-Rand
        w, h = canvas.winfo_width(), canvas.winfo_height()
        new_coords = [
            max(0, min(new_coords[0], w)),
            max(0, min(new_coords[1], h)),
            max(0, min(new_coords[2], w)),
            max(0, min(new_coords[3], h)),
        ]

        canvas.coords(self._moving_box_id, *new_coords)


    def end_move(self, event):
        """Abschluss des Bewegens: speichere Box und zeichne final neu."""
        if not self._moving or not hasattr(self, "_moving_box_id"):
            return

        # Canvas-Koordinaten in Bildkoordinaten umwandeln
        coords = self.selected_canvas.coords(self._moving_box_id)
        img_w, img_h = self.selected_image.img_size
        scale_x = self.selected_canvas.winfo_width() / img_w
        scale_y = self.selected_canvas.winfo_height() / img_h

        moved_box = self._moving_box
        moved_box["x1"] = int(coords[0] / scale_x)
        moved_box["y1"] = int(coords[1] / scale_y)
        moved_box["x2"] = int(coords[2] / scale_x)
        moved_box["y2"] = int(coords[3] / scale_y)

        # In JSON speichern
        pair = self.data_handler.current_pair()
        ctx = self.data_handler.context_info()
        self.data_handler.saver.save_box(pair, moved_box, ctx, state="annotated")

        # Zurück in die Boxliste einfügen
        self.selected_image.boxes.insert(self._moving_index, moved_box)

        # Temporäres Rechteck löschen
        self.selected_canvas.delete(self._moving_box_id)
        del self._moving_box_id

        # Finaler Redraw (einmalig!)
        self.selected_canvas.delete("box")
        self.displayer._draw_boxes(self.selected_canvas, self.selected_image.boxes)

        # Zustand zurücksetzen
        self._moving = False
        self._move_start_x = None
        self._move_start_y = None
        del self._moving_box
        del self._moving_index



class Flickerer:
    def __init__(self, ui=None):
        self.ui = ui
        self.displayer = AnnotationDisplayer()

        self._flicker_running = False
        self._show_first = True

        # will be set when flicker starts
        self.canvas = None
        self.pair = None
        self.w = None
        self.h = None
        self.interval = 500

    def start_flicker(self, canvas, pair, w, h, interval=500):
        self.canvas = canvas
        self.pair = pair
        self.w = w
        self.h = h
        self.interval = interval

        self._flicker_running = True
        self._show_first = True  # reset toggle
        self._flicker_step()

    def _flicker_step(self):
        if not self._flicker_running:
            return

        self.canvas.delete("all")
        if self._show_first:
            self.displayer._draw_image(self.canvas, self.pair.image1, self.w, self.h)
        else:
            self.displayer._draw_image(self.canvas, self.pair.image2, self.w, self.h)

        self._show_first = not self._show_first
        self.canvas.after(self.interval, self._flicker_step)

    def stop_flicker(self):
        self._flicker_running = False
        self.canvas.delete("all")
        # always stop on image2
        self.displayer._draw_image(self.canvas, self.pair.image2, self.w, self.h)
        if self.ui:
            self.ui.refresh()
    def toggle_flicker(self, canvas, pair, w, h, interval=500):
        if self._flicker_running:
            self.stop_flicker()
        else:
            self.start_flicker(canvas, pair, w, h, interval)



class Crosshair:
    def __init__(self, canvas: tk.Canvas, color="gray", width=8):
        self.canvas = canvas
        self.color = color
        self.width = width

        self._hline = None
        self._vline = None

        # Binde Mausbewegung
        self.canvas.bind("<Motion>", self._on_mouse_move)
        # Crosshair verschwindet, wenn Maus den Canvas verlässt
        self.canvas.bind("<Leave>", self._on_mouse_leave)

    def _on_mouse_move(self, event):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        # Existierende Linien löschen
        if self._hline is not None:
            self.canvas.delete(self._hline)
        if self._vline is not None:
            self.canvas.delete(self._vline)

        # Neue Linien zeichnen
        self._hline = self.canvas.create_line(
            0, event.y, w, event.y,
            fill=self.color, width=self.width, dash=(2, 2)
        )
        self._vline = self.canvas.create_line(
            event.x, 0, event.x, h,
            fill=self.color, width=self.width, dash=(2, 2)
        )

    def _on_mouse_leave(self, event):
        if self._hline is not None:
            self.canvas.delete(self._hline)
            self._hline = None
        if self._vline is not None:
            self.canvas.delete(self._vline)
            self._vline = None
