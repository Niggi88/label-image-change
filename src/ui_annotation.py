import uuid

class BoxHandler:
    def __init__(self, pair_loader, saver):
        self.pair = pair_loader
        self.saver = saver

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
        if self.current_rect:
            canvas.delete(self.current_rect)
        self.current_rect = canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline="red", width=2
        )

    def end_box(self, event, canvas, annot_img):
        if self.start_x is None:
            return
        if not getattr(self, "_drawing", False):
            return  # it was just a click → selection already handled
        self._drawing = False

        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        self.start_x = self.start_y = None

        # Ignore tiny boxes
        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
            if self.current_rect:
                canvas.delete(self.current_rect)
            self.current_rect = None
            return

        scale_x = annot_img.img_size[0] / canvas.winfo_width()
        scale_y = annot_img.img_size[1] / canvas.winfo_height()
        # Build full box
        box = {
            "x1": int(min(x1, x2) * scale_x),
            "y1": int(min(y1, y2) * scale_y),
            "x2": int(max(x1, x2) * scale_x),
            "y2": int(max(y1, y2) * scale_y),
            "annotation_type": "item_removed" if annot_img.image_id == 1 else "item_added",
            "pair_id": str(uuid.uuid4()),
        }

        # Add to in-memory list
        annot_img.boxes.append(box)

        # Draw all boxes for this image
        # self.display_boxes(canvas, annot_img.boxes)
        self.current_rect = None

        # Save immediately
        self.saver.save_box(self.pair, box, state="annotated")




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

