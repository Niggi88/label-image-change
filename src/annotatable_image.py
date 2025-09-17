import tkinter as tk
from tkinter import ttk
from segment_box import segment
import numpy as np
from utils import resize_with_aspect_ratio
from PIL import Image, ImageTk
from config import *
import cv2
import io
import base64
from image_annotation import ImageAnnotation
import uuid
from pathlib import Path

    
class AnnotationTypeState():
    POSITIVE = "green"
    NEGATIVE = "red"


class AnnotatableImage(ttk.Frame):
    """A widget that can display an image and its annotations"""
    def __init__(self, container, annotation_controller, controller):
        super().__init__(container)
        self.canvas = tk.Canvas(self)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Configure>", self._resize_image)
        self._original_pil_image = None   # Speichere Original
        self._image = None

        _id = 1 if str(self).endswith("e") else 2
        
        self.image_id = None


        # Drawing state
        self.drawing = False
        self.start_x = None
        self.start_y = None

        # self.selected_box_index = None

        self.annotation_type_state = (
            ImageAnnotation.Classes.ANNOTATION_X if _id == 1 else ImageAnnotation.Classes.ANNOTATION
        )

        self.annotation_controller = annotation_controller
        self.controller = controller


        self.box_handler = BoxHandler(self, self.canvas)

        self.canvas.bind('<Button-1>', self.box_handler.start_box)
        self.canvas.bind('<B1-Motion>', self.box_handler.draw_box)
        self.canvas.bind('<ButtonRelease-1>', self.box_handler.end_box)
        
        self._image = None  # Keep reference to avoid garbage collection
        self._scale_factor = 1.0
    
        self.moving_box = False
        self.move_start_x = None
        self.move_start_y = None
        self.moving_box_index = None
        self.move_start_coords = None


        self.canvas.bind("<Button-3>", self.box_handler.on_right_click)
        self.canvas.bind("<B3-Motion>", self.box_handler.on_right_drag)
        self.canvas.bind("<ButtonRelease-3>", self.box_handler.on_right_release)


        self.crosshair_lines = []
        self.canvas.bind("<Motion>", self.show_crosshair)
        self.canvas.bind("<Leave>", lambda e: self.clear_crosshair())

    def show_crosshair(self, event):
        self.clear_crosshair()

        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        horiz = self.canvas.create_line(0, y, width, y, fill="gray", dash=(2, 2), tags="crosshair", width=8)
        vert = self.canvas.create_line(x, 0, x, height, fill="gray", dash=(2, 2), tags="crosshair", width=8)
        self.crosshair_lines = [horiz, vert]


    def clear_crosshair(self):
        for line in self.crosshair_lines:
            self.canvas.delete(line)
        self.crosshair_lines = []


    def load_image(self, image_source, boxes=None, image_id=None):
        """
        Lädt ein Bild für Annotation (Session-Mode) oder Review (Unsure-Mode).
        - image_source: Pfad (str/Path) oder Bytes
        - boxes: optionale Box-Liste
        - image_id: optionale eindeutige ID (z.B. URL oder Dateiname); 
                    wird im Unsure-Mode genutzt
        """
        import io
        from pathlib import Path
        from PIL import Image
        import base64

        # PIL öffnen je nach Quelle
        if isinstance(image_source, (bytes, bytearray)):
            pil_image = Image.open(io.BytesIO(image_source)).convert("RGB")
            self.image_path = None  # kein echter Dateipfad
        else:
            self.image_path = Path(image_source)
            pil_image = Image.open(self.image_path).convert("RGB")

        self.image_size = pil_image.size
        self._original_pil_image = pil_image

        # image_id setzen
        self.image_id = image_id or (str(self.image_path) if self.image_path else None)

        self.box_handler.boxes = boxes or []

        # Anzeige vorbereiten (wie im Original)
        if self.canvas.winfo_width() > 1 and self.canvas.winfo_height() > 1:
            self._resize_image()



    def _resize_image(self, event=None):
        if self._original_pil_image is None:
            return

        # 1. Berechne Größe & Skaliere Originalbild
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            return

        resized_pil = resize_with_aspect_ratio(self._original_pil_image, canvas_width, canvas_height)
        self._image = ImageTk.PhotoImage(resized_pil)

        # 2. Scale & Offsets
        original_width, original_height = self._original_pil_image.size
        display_width, display_height = resized_pil.size
        self._scale_factor = display_width / original_width
        self._offset_x = (canvas_width - display_width) // 2
        self._offset_y = (canvas_height - display_height) // 2

        # self.canvas.delete("canvas_outline")  # make sure it's gone BEFORE drawing


        # 3. Komplettes Canvas leeren & nur das Bild rein
        self.canvas.delete("all")
        self._background_id = self.canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            anchor="center",
            image=self._image
        )

        # 5. Boxen drüber
        self.box_handler.display_boxes(self.box_handler.boxes)

        if hasattr(self, "controller") and self.controller:
            try:
                self.controller.redraw_outline()
            except Exception:
                pass

    def _calculate_scaled_size(self, size, max_size):
        """Calculate new size maintaining aspect ratio"""
        ratio = min(max_size[0] / size[0], max_size[1] / size[1])
        return (int(size[0] * ratio), int(size[1] * ratio))
    
    
    def clear_image(self):
        """Löscht das Hintergrund-Bild"""
        self.canvas.delete("all")
        self._image = None

        
    def clear_all(self):
        self.clear_image()
        self.box_handler.clear_boxes()
        self.box_handler.boxes = []
        self._original_pil_image = None



    def set_drawing_mode(self, enabled):
        """Enable or disable box drawing"""
        self.drawing = enabled
        


    def draw_canvas_outline(self, color):
        """Zieht eine farbige Umrandung um das gesamte Bild/Canvas"""
        self.canvas.delete("canvas_outline")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        self.canvas.create_rectangle(
            1, 1, width - 1, height - 1,
            outline=color,
            width=20,
            tags="canvas_outline"
        )





class BoxHandler():
    def __init__(self, annot_img, canvas):
        self.annot_img = annot_img
        self.canvas = canvas
        self.current_box = None
        self.boxes = []
        self.box_rects = []
        self.selected_box_index = None
        self.start_x = None
        self.start_y = None

    def start_box(self, event):
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            box_index = self.get_box_at(x, y)
            if box_index is not None:
                print(f"[SELECT] Box {box_index} selected by click.")
                self.select_box(box_index)
                return
            
            print("No box found, start_box")
            if not self.annot_img.drawing:
                return
            # Clamp innerhalb Bild-Bereich:
            img_left = self.annot_img._offset_x
            img_right = self.annot_img._offset_x + self.annot_img._original_pil_image.width * self.annot_img._scale_factor
            img_top = self.annot_img._offset_y
            img_bottom = self.annot_img._offset_y + self.annot_img._original_pil_image.height * self.annot_img._scale_factor

            self.start_x = max(img_left, min(event.x, img_right))
            self.start_y = max(img_top, min(event.y, img_bottom))
        
    def draw_box(self, event):
        if not self.annot_img.drawing or self.start_x is None:
            return

        img_left = self.annot_img._offset_x
        img_right = self.annot_img._offset_x + self.annot_img._original_pil_image.width * self.annot_img._scale_factor
        img_top = self.annot_img._offset_y
        img_bottom = self.annot_img._offset_y + self.annot_img._original_pil_image.height * self.annot_img._scale_factor

        # Clamp Maus innerhalb Bild
        x = max(img_left, min(event.x, img_right))
        y = max(img_top, min(event.y, img_bottom))

        if self.current_box:
            self.canvas.delete(self.current_box)

        self.current_box = self.canvas.create_rectangle(
            self.start_x, self.start_y,
            x, y,
            outline='blue',
            width=2,
        )

    
    def end_box(self, event):
        if not self.annot_img.drawing or self.start_x is None:
            return

        # Begrenze Endpunkt INNERHALB Bildbereich
        img_left = self.annot_img._offset_x
        img_right = self.annot_img._offset_x + self.annot_img._original_pil_image.width * self.annot_img._scale_factor
        img_top = self.annot_img._offset_y
        img_bottom = self.annot_img._offset_y + self.annot_img._original_pil_image.height * self.annot_img._scale_factor

        x = max(img_left, min(event.x, img_right))
        y = max(img_top, min(event.y, img_bottom))

        pair_id = str(uuid.uuid4())

        box = {
            'annotation_type': self.annotation_type_state,
            'x1': int((min(self.start_x, x) - self.annot_img._offset_x) / self.annot_img._scale_factor),
            'y1': int((min(self.start_y, y) - self.annot_img._offset_y) / self.annot_img._scale_factor),
            'x2': int((max(self.start_x, x) - self.annot_img._offset_x) / self.annot_img._scale_factor),
            'y2': int((max(self.start_y, y) - self.annot_img._offset_y) / self.annot_img._scale_factor),
            'pair_id': pair_id,
        }

        width = abs(box['x2'] - box['x1'])
        height = abs(box['y2'] - box['y1'])

        if width < 5 or height < 5:
            print("Ignored: too small to be a valid box.")
            return

        self.boxes.append(box)

        # Gegenstück synchronisieren (ohne Maske!)
        other_image = self.annot_img.controller.image2 if self is self.annot_img.controller.image1 else self.annot_img.controller.image1
        other_box = box.copy()
        # Explicitly set inverse annotation type
        other_box['annotation_type'] = (
            ImageAnnotation.Classes.ANNOTATION
            if self.annotation_type_state == ImageAnnotation.Classes.ANNOTATION_X
            else ImageAnnotation.Classes.ANNOTATION_X
        )
        other_box['pair_id'] = pair_id
        other_box['synced_highlight'] = True
        other_image.boxes.append(other_box)

        self.clear_boxes()
        self.display_boxes(self.boxes)

        other_image.clear_boxes()
        other_image.display_boxes(other_image.boxes)

        self.start_x = None
        self.start_y = None
        self.current_box = None

        # 1. Check & correct pair_state
        current_annotation = self.controller.annotations.get_pair_annotation(self.controller.current_index)
        if current_annotation.get("pair_state") in [
            ImageAnnotation.Classes.CHAOS,
            ImageAnnotation.Classes.NOTHING,
            ImageAnnotation.Classes.NO_ANNOTATION,
        ]:
            print("[end_box] Overriding prior state with 'annotated'")

            self.controller.annotations.set_pair_state(
                self.controller.current_index,
                ImageAnnotation.Classes.ANNOTATED
            )

        # 2. Save new annotation state (also saves boxes + pair_state)
        self.annot_img.controller._maybe_save(pair_state=ImageAnnotation.Classes.ANNOTATED)


        if self.current_box:
            self.canvas.delete(self.current_box)
            self.current_box = None

        # 4. UI update (outline + button highlight)
        self.annot_img.controller.update_ui_state(ImageAnnotation.Classes.ANNOTATED)




    def display_boxes(self, boxes, color="green"):
        """Display a list of boxes (in original image coordinates)"""
        self.clear_boxes()

        for idx, box in enumerate(boxes):
            annotation_type = box.get("annotation_type", None)
            is_selected = (self.selected_box_index is not None and idx == self.selected_box_index)
            is_synced = box.get("synced_highlight", False)

            # # 🎨 Color purely based on annotation_type
            # if annotation_type == ImageAnnotation.Classes.ANNOTATION:
            #     outline = "green"
            # elif annotation_type == ImageAnnotation.Classes.ANNOTATION_X:
            #     outline = "red"
            # else:
            #     outline = "#B497B8"


            if is_synced:
                outline = "red"
            else:
                outline = "green"


            # Highlight selected box
            if is_selected:
                outline = "blue"
                dash = (4, 2)
            elif is_synced:
                dash = (4, 2)
            else:
                dash = None

            # Scaled position
            scaled_box = {
                'x1': box['x1'] * self.annot_img._scale_factor + self.annot_img._offset_x,
                'y1': box['y1'] * self.annot_img._scale_factor + self.annot_img._offset_y,
                'x2': box['x2'] * self.annot_img._scale_factor + self.annot_img._offset_x,
                'y2': box['y2'] * self.annot_img._scale_factor + self.annot_img._offset_y
            }

            # 📐 Visual styles
            width = 6 if is_selected else 4
            dash = (4, 2) if is_synced else None

            rect_id = self.canvas.create_rectangle(
                scaled_box['x1'], scaled_box['y1'],
                scaled_box['x2'], scaled_box['y2'],
                outline=outline,
                fill="",
                width=width,
                dash=dash
            )
            self.box_rects.append(rect_id)
            # self.canvas.tag_bind(rect_id, "<Button-1>", lambda e, i=idx: self.select_box(i))



    def select_box(self, index):
        """Markiere eine Box als ausgewählt"""
        print(f"Selected box {index}")
        self.selected_box_index = index
        self.update_box_highlight()
        # Alles neu zeichnen — aber KEIN clear_boxes hier!
        # self.display_boxes(self.boxes)  # Du brauchst nichts zu löschen, weil display_boxes das immer tut.

    def update_box_highlight(self):
        for idx, rect_id in enumerate(self.box_rects):
            if idx == self.selected_box_index:
                self.canvas.itemconfig(rect_id, outline="blue", width=4, dash=(4, 2))
            else:
                self.canvas.itemconfig(rect_id, width=2, dash=None)

    def delete_selected_box(self):
        if self.selected_box_index is None:
            print("No box selected!")
            return

        pair_id = self.boxes[self.selected_box_index].get('pair_id')
        print(f"Deleting pair_id: {pair_id}")

        # 1) Delete all boxes with this pair_id on BOTH images
        self.boxes = [b for b in self.boxes if b.get('pair_id') != pair_id]
        other_image = self.annot_img.controller.image2 if self is self.annot_img.controller.image1 else self.annot_img.controller.image1
        other_image.boxes = [b for b in other_image.boxes if b.get('pair_id') != pair_id]


        # 3) Redraw boxes
        self.clear_boxes(); self.display_boxes(self.boxes)
        other_image.clear_boxes(); other_image.display_boxes(other_image.boxes)

        # 4) Redraw masks via resize
        self._resize_image()
        other_image._resize_image()

        # 5) Reset selection
        self.selected_box_index = None
        other_image.selected_box_index = None

        # 6) Derive new pair_state from LIVE canvas boxes (same logic as annotation mode)
        if not self.boxes and not other_image.boxes:
            new_state = ImageAnnotation.Classes.NO_ANNOTATION
        else:
            new_state = ImageAnnotation.Classes.ANNOTATED

        # 7) SAVE:
        self.annot_img.controller._maybe_save(pair_state=new_state)


        # 8) Update outline/buttons
        self.annot_img.controller.update_ui_state(new_state)
        print("Deleted pair in both images & masks updated immediately.")


    def clear_boxes(self):
        for rect in self.box_rects:
            self.canvas.delete(rect)
        self.box_rects = []

        # 🧼 NEW: remove temp blue drawing
        if self.current_box:
            self.canvas.delete(self.current_box)
            self.current_box = None

        self.selected_box_index = None

    def on_right_release(self, event):
        if self.moving_box_index is not None:
            print(f"[MOVE] Finished moving box {self.moving_box_index}")

            moved_box = self.boxes[self.moving_box_index]
            pair_id = moved_box.get("pair_id")
            if not pair_id:
                print("[WARN] Moved box has no pair_id.")
                return

            # TODO: This is not defined correctly!! i think should not be defined using controller
            # Get the mirrored box in the other image
            other_image = self.annot_img.controller.image2 if self is self.annot_img.controller.image1 else self.annot_img.controller.image1
            for box in other_image.boxes:
                if box.get("pair_id") == pair_id:
                    # Update position
                    box["x1"] = moved_box["x1"]
                    box["y1"] = moved_box["y1"]
                    box["x2"] = moved_box["x2"]
                    box["y2"] = moved_box["y2"]
                    break
            else:
                print("[WARN] No mirrored box found.")

            # Redraw boxes in both views
            self.display_boxes(self.boxes)
            other_image.display_boxes(other_image.boxes)

            # Auto-save
            if self.annot_img.controller:
                self.annot_img.controller.save_current_boxes()

            # Reset state
            self.moving_box_index = None
            self.move_start_coords = None

    def on_right_click(self, event):
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)

            # Get index of the box at the clicked location
            index = self.get_box_at(x, y)  # ✅ this returns an integer index

            if index is not None:
                self.moving_box_index = index
                self.move_start_coords = (x, y)
                print(f"[MOVE] Selected box {index} for moving")
            else:
                print("[MOVE] No box at clicked position")

    def get_box_at(self, x, y):
        """Return index of box that contains (canvas-x, canvas-y) by converting to image-space"""
        image_x = int((x - self.annot_img._offset_x) / self.annot_img._scale_factor)
        image_y = int((y - self.annot_img._offset_y) / self.annot_img._scale_factor)

        for i, box in enumerate(self.boxes):
            if box["x1"] <= image_x <= box["x2"] and box["y1"] <= image_y <= box["y2"]:
                return i
        return None

    def get_boxes(self):
        """Return only boxes that were manually drawn (not mirrored)"""
        return [b for b in self.boxes if not b.get("synced_highlight", False)]
        # return self.boxes  # ⚠️ für Debug, nicht dauerhaft!

    def on_right_drag(self, event):
        if self.moving_box_index is None:
            return

        new_x = self.canvas.canvasx(event.x)
        new_y = self.canvas.canvasy(event.y)

        dx = new_x - self.move_start_coords[0]
        dy = new_y - self.move_start_coords[1]

        box = self.boxes[self.moving_box_index]
        box["x1"] += dx
        box["y1"] += dy
        box["x2"] += dx
        box["y2"] += dy

        self.move_start_coords = (new_x, new_y)

        self.display_boxes(self.boxes)



    def delete_selected_box(self):
        if self.selected_box_index is None:
            print("No box selected!")
            return

        # Finde die pair_id der ausgewählten Box
        pair_id = self.boxes[self.selected_box_index].get('pair_id')
        print(f"Deleting box pair_id: {pair_id}")

        # Lösche ALLE Boxen mit dieser pair_id in diesem Bild
        self.boxes = [b for b in self.boxes if b.get('pair_id') != pair_id]

        # Gleiche Box auch im anderen Bild löschen:
        other_image = self.annot_img.controller.image2 if self is self.annot_img.controller.image1 else self.annot_img.controller.image1
        other_image.boxes = [b for b in other_image.boxes if b.get('pair_id') != pair_id]

        # Clear & redraw
        self.clear_boxes()
        self.display_boxes(self.boxes)

        other_image.clear_boxes()
        other_image.display_boxes(other_image.boxes)

        self.selected_box_index = None
        other_image.selected_box_index = None
        print("Deleted box in both images.")

    