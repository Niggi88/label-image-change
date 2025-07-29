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
# from app import ImagePairViewer



def mask_pil_to_base64(pil_image):
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

def create_transparent_overlay(mask_array, color=(30, 144, 255), alpha=120):
    """
    Baut ein RGBA-Overlay:
    - color: RGB Farbe (Blau standardmäßig)
    - alpha: Transparenz (0–255)
    Nur Vordergrund (mask==1) wird eingefärbt.
    """
    # 👉 Single-Channel sicherstellen
    if mask_array.ndim == 3:
        print("Mask had multiple channels — using first channel only!")
        mask_array = mask_array[..., 0]

    print("Mask unique values:", np.unique(mask_array))
    h, w = mask_array.shape

    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[..., :3] = color
    rgba[..., 3] = (mask_array > 0).astype(np.uint8) * alpha

    return Image.fromarray(rgba)

def combine_masks(mask_list):
    if not mask_list:
        return None
    base = mask_list[0].copy()
    for mask in mask_list[1:]:
        base = Image.alpha_composite(base, mask)
    return base

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
        
        self._mask_ids = []
        self.image_id = None

        # Drawing state
        self.drawing = False
        self.start_x = None
        self.start_y = None
        self.current_box = None
        self.boxes = []
        self.box_rects = []
        # self.selected_box_index = None
        self._original_mask_pil = None
        self._original_mask_pils = []

        # self.annotation_type_state = AnnotationTypeState.NEGATIVE if _id == 1 else AnnotationTypeState.POSITIVE

        self.annotation_type_state = (
            ImageAnnotation.Classes.ANNOTATION_X if _id == 1 else ImageAnnotation.Classes.ANNOTATION
        )

        self.annotation_controller = annotation_controller
        self.controller = controller
        # assert isinstance(annotation_controller, ImageAnnotation) 
        # assert isinstance(controller, ImagePairViewer)
        # Bind mouse events for drawing
        self.canvas.bind('<Button-1>', self.start_box)
        self.canvas.bind('<B1-Motion>', self.draw_box)
        self.canvas.bind('<ButtonRelease-1>', self.end_box)
        
        self._image = None  # Keep reference to avoid garbage collection
        self._scale_factor = 1.0
    
    # def load_image(self, image_path, max_size=(IMAGE_SIZE, IMAGE_SIZE)):
    #     """Load and display an image using existing resize method"""
    #     print("loaded image", image_path)
    #     pil_image = Image.open(image_path)
        
    #     # Store original size for scaling factor calculation
    #     original_size = pil_image.size
        
    #     # Use existing resize method
    #     pil_image = resize_with_aspect_ratio(pil_image, *max_size)
    #     self._image = ImageTk.PhotoImage(pil_image)
        
    #     # Calculate scale factor based on the resize results
    #     self._scale_factor = pil_image.size[0] / original_size[0]
        
    #     # Update canvas size and display image
    #     self.canvas.config(width=pil_image.size[0], height=pil_image.size[1])
    #     self.canvas.create_image(0, 0, anchor="nw", image=self._image)



    def load_image(self, image_path, boxes=None):
        self.image_path = image_path
        pil_image = Image.open(image_path)
        self.image_size = pil_image.size
        self._original_pil_image = pil_image

        self._original_mask_pils = []  # <--- WICHTIG: Liste leeren!
        self.boxes = boxes or []

        
        for box in self.boxes:
            from image_annotation import make_absolute_path

            annotations_meta = self.controller.annotations.annotations.get("_meta", {})
            box_abs_path = make_absolute_path(box.get("mask_image_id"), annotations_meta)

            if 'mask_base64' in box and box_abs_path == str(self.image_path):
                mask_bytes = base64.b64decode(box['mask_base64'])
                mask_pil = Image.open(io.BytesIO(mask_bytes)).convert("RGBA")
                self._original_mask_pils.append(mask_pil)

        if self.canvas.winfo_width() > 1 and self.canvas.winfo_height() > 1:
            self._resize_image()


    # def _resize_image(self, event=None):
    #     if self._original_pil_image is None:
    #         return

    #     canvas_width = self.canvas.winfo_width()
    #     canvas_height = self.canvas.winfo_height()
        
    #     if canvas_width <= 1 or canvas_height <= 1:
    #         return  # Vermeidet width/height = 0 Fehler!

    #     resized_pil = resize_with_aspect_ratio(
    #         self._original_pil_image,
    #         canvas_width,
    #         canvas_height
    #     )
        
    #     self._image = ImageTk.PhotoImage(resized_pil)


    #     # === NEU: Maske synchron skalieren ===
    #     if self._original_mask_pil:
    #         resized_mask = resize_with_aspect_ratio(
    #             self._original_mask_pil,
    #             canvas_width,
    #             canvas_height
    #         )
    #         self._mask_overlay = ImageTk.PhotoImage(resized_mask)
    #     else:
    #         self._mask_overlay = None

    #     # === NEU: Berechne Scale & Offsets ===
    #     original_width, original_height = self._original_pil_image.size
    #     display_width, display_height = resized_pil.size

    #     self._scale_factor = display_width / original_width
    #     self._offset_x = (canvas_width - display_width) // 2
    #     self._offset_y = (canvas_height - display_height) // 2
        
    #     self.canvas.delete("all")
    #     self.canvas.create_image(
    #         canvas_width // 2,
    #         canvas_height // 2,
    #         anchor="center",
    #         image=self._image
    #     )

    #     # Maske drüberlegen, wenn vorhanden
    #     if self._mask_overlay:
    #         self.display_mask()
    #     if self.boxes:
    #         self.display_boxes(self.boxes)

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

        # 3. Komplettes Canvas leeren & nur das Bild rein
        self.canvas.delete("all")
        self._background_id = self.canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            anchor="center",
            image=self._image
        )
        # 4. Maske drüber, wenn vorhanden
        self.display_mask()

        # 5. Boxen drüber
        self.display_boxes(self.boxes)



    def _calculate_scaled_size(self, size, max_size):
        """Calculate new size maintaining aspect ratio"""
        ratio = min(max_size[0] / size[0], max_size[1] / size[1])
        return (int(size[0] * ratio), int(size[1] * ratio))
    
    def start_box(self, event):
        if not self.drawing:
            return
        # Clamp innerhalb Bild-Bereich:
        img_left = self._offset_x
        img_right = self._offset_x + self._original_pil_image.width * self._scale_factor
        img_top = self._offset_y
        img_bottom = self._offset_y + self._original_pil_image.height * self._scale_factor

        self.start_x = max(img_left, min(event.x, img_right))
        self.start_y = max(img_top, min(event.y, img_bottom))
    
    def draw_box(self, event):
        if not self.drawing or self.start_x is None:
            return

        img_left = self._offset_x
        img_right = self._offset_x + self._original_pil_image.width * self._scale_factor
        img_top = self._offset_y
        img_bottom = self._offset_y + self._original_pil_image.height * self._scale_factor

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

    
    # def end_box(self, event):
    #     if not self.drawing or self.start_x is None:
    #         return

    #     # Begrenze Endpunkt INNERHALB Bildbereich
    #     img_left = self._offset_x
    #     img_right = self._offset_x + self._original_pil_image.width * self._scale_factor
    #     img_top = self._offset_y
    #     img_bottom = self._offset_y + self._original_pil_image.height * self._scale_factor

    #     x = max(img_left, min(event.x, img_right))
    #     y = max(img_top, min(event.y, img_bottom))

    #     pair_id = str(uuid.uuid4())

    #     box = {
    #         'annotation_type': self.annotation_type_state,
    #         'x1': int((min(self.start_x, x) - self._offset_x) / self._scale_factor),
    #         'y1': int((min(self.start_y, y) - self._offset_y) / self._scale_factor),
    #         'x2': int((max(self.start_x, x) - self._offset_x) / self._scale_factor),
    #         'y2': int((max(self.start_y, y) - self._offset_y) / self._scale_factor),
    #         'pair_id': pair_id,
    #     }

    #     width = abs(box['x2'] - box['x1'])
    #     height = abs(box['y2'] - box['y1'])

    #     if width < 5 or height < 5:
    #         print("Ignored: too small to be a valid box.")
    #         return

    #     self.boxes.append(box)

    #     # 👉 Gegenstück synchronisieren (ohne Maske!)
    #     other_image = self.controller.image2 if self is self.controller.image1 else self.controller.image1
    #     other_box = box.copy()
    #     other_box['annotation_type'] = other_image.annotation_type_state
    #     other_box['pair_id'] = pair_id
    #     other_box['synced_highlight'] = True
    #     other_image.boxes.append(other_box)

    #     self.clear_boxes()
    #     self.display_boxes(self.boxes)

    #     other_image.clear_boxes()
    #     other_image.display_boxes(other_image.boxes)

    #     self.start_x = None
    #     self.start_y = None
    #     self.current_box = None

    #     # Nur HIER Masken-API für das annotierte Bild
    #     self.generate_mask_from_bbox()

    #     # Falls CHAOS, NOTHING, NO_ANNOTATION → in ANNOTATED ändern
    #     annotation = self.controller.annotations.get_pair_annotation(self.controller.current_index)
    #     if annotation.get("pair_state") in [
    #         ImageAnnotation.Classes.CHAOS,
    #         ImageAnnotation.Classes.NOTHING,
    #         ImageAnnotation.Classes.NO_ANNOTATION,
    #     ]:
    #         print("[end_box] Overriding prior state with 'annotated'")
    #         self.controller.annotations.set_pair_state(
    #             self.controller.current_index,
    #             ImageAnnotation.Classes.ANNOTATED
    #         )
    #         self.controller.state = ImageAnnotation.Classes.ANNOTATED

    #         # ❗ WICHTIG: Outline sofort löschen
    #         self.controller.image1.canvas.delete("canvas_outline")
    #         self.controller.image2.canvas.delete("canvas_outline")

    #         # Buttons aktualisieren
    #         self.controller.reset_buttons()
    #         self.controller.annotate_btn.state(['pressed'])

    def end_box(self, event):
        if not self.drawing or self.start_x is None:
            return

        # Begrenze Endpunkt INNERHALB Bildbereich
        img_left = self._offset_x
        img_right = self._offset_x + self._original_pil_image.width * self._scale_factor
        img_top = self._offset_y
        img_bottom = self._offset_y + self._original_pil_image.height * self._scale_factor

        x = max(img_left, min(event.x, img_right))
        y = max(img_top, min(event.y, img_bottom))

        pair_id = str(uuid.uuid4())

        box = {
            'annotation_type': self.annotation_type_state,
            'x1': int((min(self.start_x, x) - self._offset_x) / self._scale_factor),
            'y1': int((min(self.start_y, y) - self._offset_y) / self._scale_factor),
            'x2': int((max(self.start_x, x) - self._offset_x) / self._scale_factor),
            'y2': int((max(self.start_y, y) - self._offset_y) / self._scale_factor),
            'pair_id': pair_id,
        }

        width = abs(box['x2'] - box['x1'])
        height = abs(box['y2'] - box['y1'])

        if width < 5 or height < 5:
            print("Ignored: too small to be a valid box.")
            return

        self.boxes.append(box)

        # 👉 Gegenstück synchronisieren (ohne Maske!)
        other_image = self.controller.image2 if self is self.controller.image1 else self.controller.image1
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

        # 🧠 1. Check & correct pair_state
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

        # 🧠 2. Save new annotation state (also saves boxes + pair_state)
        self.controller.annotations.save_pair_annotation(
            image1=self,
            image2=other_image,
            pair_state=ImageAnnotation.Classes.ANNOTATED
        )

        # 🧠 3. Generate mask
        self.generate_mask_from_bbox()

        if self.current_box:
            self.canvas.delete(self.current_box)
            self.current_box = None

        # 🧠 4. UI update (outline + button highlight)
        self.controller.update_ui_state(ImageAnnotation.Classes.ANNOTATED)




    def display_mask(self):
        if not self._original_mask_pils:
            return

        if not self._original_mask_pils:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            print("Canvas not ready yet, skipping mask display.")
            return  # Avoid crashing on app start

    # proceed to resize masks

        # Alte Masken-Canvas-IDs löschen:
        if hasattr(self, '_mask_ids'):
            for mid in self._mask_ids:
                self.canvas.delete(mid)
        self._mask_ids = []
        self._mask_overlays = []

        for mask_pil in self._original_mask_pils:
            resized_mask = resize_with_aspect_ratio(
                mask_pil,
                self.canvas.winfo_width(),
                self.canvas.winfo_height()
            )
            mask_overlay = ImageTk.PhotoImage(resized_mask)
            mask_id = self.canvas.create_image(
                self.canvas.winfo_width() // 2,
                self.canvas.winfo_height() // 2,
                anchor="center",
                image=mask_overlay
            )
            self.canvas.tag_raise(mask_id, self._background_id)
            self._mask_ids.append(mask_id)
            self._mask_overlays.append(mask_overlay)

            
    # def display_boxes(self, boxes, color="green"):
    #     """Display a list of boxes (in original image coordinates)"""
    #     self.clear_boxes()

    #     for idx, box in enumerate(boxes):
    #         annotation_type = box.get("annotation_type", None)

    #         if annotation_type == ImageAnnotation.Classes.ANNOTATION:
    #             outline = "green"
    #         elif annotation_type == ImageAnnotation.Classes.ANNOTATION_X:
    #             outline = "red"
    #         elif box.get('synced_highlight', False):
    #             outline = "red"
    #         elif self.selected_box_index is not None and idx == self.selected_box_index:
    #             outline = "red"
    #         else:
    #             outline = "grey"  # fallback if annotation_type is missing

    #         scaled_box = {
    #             'x1': box['x1'] * self._scale_factor + self._offset_x,
    #             'y1': box['y1'] * self._scale_factor + self._offset_y,
    #             'x2': box['x2'] * self._scale_factor + self._offset_x,
    #             'y2': box['y2'] * self._scale_factor + self._offset_y
    #         }
    #         rect_id = self.canvas.create_rectangle(
    #             scaled_box['x1'], scaled_box['y1'],
    #             scaled_box['x2'], scaled_box['y2'],
    #             outline=outline, # if self.selected_box_index is not None and idx == self.selected_box_index else color,
    #             fill="",  # oder transparente Fläche
    #             width=2
    #         )
    #         self.box_rects.append(rect_id)
    #         self.canvas.tag_bind(rect_id, "<Button-1>", lambda e, i=idx: self.select_box(i))
    #         self.display_mask()

    def display_boxes(self, boxes, color="green"):
        """Display a list of boxes (in original image coordinates)"""
        self.clear_boxes()

        for idx, box in enumerate(boxes):
            annotation_type = box.get("annotation_type", None)
            is_selected = (self.selected_box_index is not None and idx == self.selected_box_index)
            is_synced = box.get("synced_highlight", False)

            # 🎨 Color purely based on annotation_type
            if annotation_type == ImageAnnotation.Classes.ANNOTATION:
                outline = "green"
            elif annotation_type == ImageAnnotation.Classes.ANNOTATION_X:
                outline = "red"
            else:
                outline = "grey"

            # ✏️ Highlight selected box
            if is_selected:
                outline = "blue"

            # 📏 Scaled position
            scaled_box = {
                'x1': box['x1'] * self._scale_factor + self._offset_x,
                'y1': box['y1'] * self._scale_factor + self._offset_y,
                'x2': box['x2'] * self._scale_factor + self._offset_x,
                'y2': box['y2'] * self._scale_factor + self._offset_y
            }

            # 📐 Visual styles
            width = 4 if is_selected else 2
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
            self.canvas.tag_bind(rect_id, "<Button-1>", lambda e, i=idx: self.select_box(i))

        self.display_mask()



    def select_box(self, index):
        """Markiere eine Box als ausgewählt"""
        print(f"Selected box {index}")
        self.selected_box_index = index
        self.update_box_highlight()
        # Alles neu zeichnen — aber KEIN clear_boxes hier!
        # self.display_boxes(self.boxes)  # Du brauchst nichts zu löschen, weil display_boxes das immer tut.

    def update_box_highlight(self):
        """Nur Farben der Boxen updaten"""
        for idx, rect_id in enumerate(self.box_rects):
            color = "red" if idx == self.selected_box_index else "green"
            self.canvas.itemconfig(rect_id, outline=color)

    def delete_selected_box(self):
        if self.selected_box_index is None:
            print("No box selected!")
            return

        pair_id = self.boxes[self.selected_box_index].get('pair_id')
        print(f"Deleting pair_id: {pair_id}")

        # 1) Lösche alle Boxen mit dieser ID in beiden Bildern
        self.boxes = [b for b in self.boxes if b.get('pair_id') != pair_id]
        other_image = self.controller.image2 if self is self.controller.image1 else self.controller.image1
        other_image.boxes = [b for b in other_image.boxes if b.get('pair_id') != pair_id]

        # 2) Maskenlisten für beide Bilder AKTUALISIEREN
        self._original_mask_pils = [
            Image.open(io.BytesIO(base64.b64decode(b['mask_base64']))).convert("RGBA")
            for b in self.boxes
            if "mask_base64" in b and b["mask_image_id"] == str(self.image_path)
        ]

        other_image._original_mask_pils = [
            Image.open(io.BytesIO(base64.b64decode(b['mask_base64']))).convert("RGBA")
            for b in other_image.boxes
            if "mask_base64" in b and b["mask_image_id"] == str(other_image.image_path)
        ]

        # 3) Neu zeichnen
        self.clear_boxes()
        self.display_boxes(self.boxes)
        other_image.clear_boxes()
        other_image.display_boxes(other_image.boxes)

        # 4) Neu zeichnen der Masken über _resize_image
        self._resize_image()
        other_image._resize_image()
       
        # 5) Auswahl zurücksetzen
        self.selected_box_index = None
        other_image.selected_box_index = None

        # 6) Wenn keine Boxen mehr übrig sind → pair_state auf "no_annotation"
        if not self.boxes and not other_image.boxes:
            new_state = ImageAnnotation.Classes.NO_ANNOTATION
        else:
            new_state = ImageAnnotation.Classes.ANNOTATED

        # Save correct state!
        self.controller.annotations.save_pair_annotation(
            image1=self,
            image2=other_image,
            pair_state=new_state
        )

        # 🔄 Update UI outline & buttons
        self.controller.update_ui_state(new_state)
        print("Deleted pair in both images & masks updated immediately.")



        
    # def clear_boxes(self):
    #     """Clear all boxes from display"""
    #     self.boxes = []
    #     # Keep the image, delete everything else
    #     self.canvas.delete("all")
    #     if self._image:
    #         self.canvas.create_image(0, 0, anchor="nw", image=self._image)
    
    def clear_image(self):
        """Löscht das Hintergrund-Bild"""
        self.canvas.delete("all")
        self._image = None

    def clear_boxes(self):
        for rect in self.box_rects:
            self.canvas.delete(rect)
        self.box_rects = []

        # 🧼 NEW: remove temp blue drawing
        if self.current_box:
            self.canvas.delete(self.current_box)
            self.current_box = None

        self.selected_box_index = None


    def clear_mask(self):
        """Löscht nur die Maske"""
        if hasattr(self, '_mask_ids'):
            for mid in self._mask_ids:
                self.canvas.delete(mid)
            self._mask_ids = []
        
        self._original_mask_pils = []
        self._mask_overlays = []

    def clear_all(self):
        self.clear_image()
        self.clear_mask()
        self.clear_boxes()
        self.boxes = []
        self._original_pil_image = None



    def set_drawing_mode(self, enabled):
        """Enable or disable box drawing"""
        self.drawing = enabled
        
    def get_boxes(self):
        """Return only boxes that were manually drawn (not mirrored)"""
        return [b for b in self.boxes if not b.get("synced_highlight", False)]
        # return self.boxes  # ⚠️ für Debug, nicht dauerhaft!


    def draw_canvas_outline(self, color):
        """Zieht eine farbige Umrandung um das gesamte Bild/Canvas"""
        self.canvas.delete("canvas_outline")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        self.canvas.create_rectangle(
            1, 1, width - 1, height - 1,
            outline=color,
            width=5,
            tags="canvas_outline"
        )



    def generate_mask_from_bbox(self):
        """Nimmt die zuletzt gezeichnete BBox, ruft FastAPI, speichert Maske & aktualisiert Anzeige"""
        if not self.boxes:
            print("No BBoxes available for segmentation!")
            return

        bbox = self.boxes[-1]
        box = np.array([bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']])
        image_np = np.array(self._original_pil_image)

        # 1) 🛰️ API-Call
        mask_pil, details = segment(image_np, box)
        # print("Segmentation done:", details)

        short_details = details.copy()
        if "mask" in short_details:
            short_details["mask"] = short_details["mask"][:10] + "..."
        print("Segmentation done:", short_details)

        if mask_pil is None:
            print("Segmentation failed — no mask to show.")
            return

        result_mask = np.array(mask_pil)
        binary_mask = (result_mask > 128).astype(np.uint8)
        new_mask = create_transparent_overlay(binary_mask)

        bbox['mask_base64'] = mask_pil_to_base64(new_mask)
        bbox['mask_image_id'] = str(self.image_path)

    

        # 2) Maskenliste neu bauen für dieses Bild
        self._original_mask_pils = []
        for box in self.boxes:
            if "mask_base64" in box and "mask_image_id" in box and box["mask_image_id"] == str(self.image_path):
                mask_bytes = base64.b64decode(box["mask_base64"])
                mask_pil = Image.open(io.BytesIO(mask_bytes)).convert("RGBA")
                self._original_mask_pils.append(mask_pil)


        
        # 3) Andere Seite nur synchronisieren (keine API, keine neue Maske)
        other_image = self.controller.image2 if self is self.controller.image1 else self.controller.image1
        other_image._original_mask_pils = []
        for box in other_image.boxes:
            if "mask_base64" in box and "mask_image_id" in box and box["mask_image_id"] == str(other_image.image_path):
                mask_bytes = base64.b64decode(box["mask_base64"])
                mask_pil = Image.open(io.BytesIO(mask_bytes)).convert("RGBA")
                other_image._original_mask_pils.append(mask_pil)


        # 5) Anzeige aktualisieren
        self._resize_image()
        other_image._resize_image()
        print("Mask displayed.")


