import uuid
from ui_annotation_displayer import AnnotationDisplayer

class BoxHandler:
    def __init__(self, pair_loader, saver, ui=None):
        self.ui = ui

        self.pair = pair_loader
        self.saver = saver
        self.displayer = AnnotationDisplayer()

        self.start_x = None
        self.start_y = None
        self.current_rect = None

        self.selected_box_index = None
        self.selected_canvas = None
        self.selected_image = None
        self._drawing = False

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
        # Lösche alten Preview
        canvas.delete("preview")
        # Zeichne neuen Preview
        self.current_rect = canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline="red", width=2, dash=(2, 2), tags="preview"
        )

    def end_box(self, event, canvas, annot_img):
        if self.start_x is None or not getattr(self, "_drawing", False):
            return
        self._drawing = False

        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        self.start_x = self.start_y = None

        # Ignoriere winzige Boxen
        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
            canvas.delete("preview")
            self.current_rect = None
            return

        # Skaliere zu Bildkoordinaten
        scale_x = annot_img.img_size[0] / canvas.winfo_width()
        scale_y = annot_img.img_size[1] / canvas.winfo_height()
        box = {
            "x1": int(min(x1, x2) * scale_x),
            "y1": int(min(y1, y2) * scale_y),
            "x2": int(max(x1, x2) * scale_x),
            "y2": int(max(y1, y2) * scale_y),
            "annotation_type": "item_removed" if annot_img.image_id == 1 else "item_added",
            "pair_id": str(uuid.uuid4()),
        }

        annot_img.boxes.append(box)
        self.saver.save_box(self.pair, box, state="annotated")

        # 🔑 Preview löschen – jetzt übernimmt refresh() das Zeichnen
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
        self.saver.save_delete_box(self.pair, removed_box["pair_id"])

        # reset selection
        self.selected_box_index = None
        self.selected_canvas = None
        self.selected_image = None

     # ---------------- MOVE ----------------

    def start_move(self, event, canvas, annot_img):
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
                print(f"Start moving box {i}")

                # 1) Entferne Box aus JSON
                self.saver.save_delete_box(self.pair, b["pair_id"])

                # 2) Entferne aus Memory
                self.selected_image.boxes.pop(i)

                # 3) Merke diese Box zum Verschieben
                self._moving_box = dict(b)   # copy the whole box
                self._moving_index = i       # remember its index
                # 4) Redraw übrige Boxes
                canvas.delete("box")
                self.displayer._draw_boxes(canvas, annot_img.boxes)

                return


    def move_box(self, event, canvas):
        if not self._moving or not hasattr(self, "_moving_box"):
            return

        dx = event.x - self._move_start_x
        dy = event.y - self._move_start_y
        self._move_start_x, self._move_start_y = event.x, event.y

        img_w, img_h = self.selected_image.img_size
        scale_x = canvas.winfo_width() / img_w
        scale_y = canvas.winfo_height() / img_h

        box = self._moving_box

        # canvas coords
        cx1, cy1 = int(box["x1"] * scale_x), int(box["y1"] * scale_y)
        cx2, cy2 = int(box["x2"] * scale_x), int(box["y2"] * scale_y)

        # apply move
        cx1 += dx; cx2 += dx
        cy1 += dy; cy2 += dy

        # back to image coords
        box["x1"] = int(cx1 / scale_x)
        box["y1"] = int(cy1 / scale_y)
        box["x2"] = int(cx2 / scale_x)
        box["y2"] = int(cy2 / scale_y)

        # redraw: draw ONLY remaining boxes + the updated moving_box
        canvas.delete("box")
        all_boxes = self.selected_image.boxes + [box]
        self.displayer._draw_boxes(canvas, all_boxes, highlight=len(all_boxes)-1)


    def end_move(self, event):
        if not self._moving or not hasattr(self, "_moving_box"):
            return

        moved_box = self._moving_box

        # Speichern
        self.saver.save_box(self.pair, moved_box)
        print(f"Moved and saved box {moved_box['pair_id']}")

        # Insert back at same index
        self.selected_image.boxes.insert(self._moving_index, moved_box)

        # Final redraw: now only the true box list
        self.selected_canvas.delete("box")
        self.displayer._draw_boxes(self.selected_canvas, self.selected_image.boxes)

        # Refresh whole UI so both canvases redraw from JSON
        root = self.selected_canvas.winfo_toplevel()
        app = root.children.get("!uielements")
        if app:
            app.refresh()
            
        # Reset
        self._moving = False
        self._move_start_x = None
        self._move_start_y = None
        del self._moving_box
        del self._moving_index
