import tkinter as tk
from tkinter import ttk
from segment_box import segment
import numpy as np
from utils import resize_with_aspect_ratio
from PIL import Image, ImageTk
from config import *
import cv2

class AnnotationTypeState():
    POSITIVE = "green"
    NEGATIVE = "red"


class AnnotatableImage(ttk.Frame):
    """A widget that can display an image and its annotations"""
    def __init__(self, container):
        super().__init__(container)
        self.canvas = tk.Canvas(self)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Configure>", self._resize_image)
        self._original_pil_image = None   # Speichere Original
        self._image = None

        _id = 1 if str(self).endswith("e") else 2
         
        # Drawing state
        self.drawing = False
        self.start_x = None
        self.start_y = None
        self.current_box = None
        self.boxes = []
        self.box_rects = []
        self.selected_box_index = None
        self._original_mask_pil = None
        self.annotation_type_state = AnnotationTypeState.NEGATIVE if _id == 1 else AnnotationTypeState.POSITIVE
        
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


    def load_image(self, image_path):
        pil_image = Image.open(image_path)
        self._original_pil_image = pil_image
    
            # << DAS ist entscheidend! >>
        if self.canvas.winfo_width() > 1 and self.canvas.winfo_height() > 1:
            self._resize_image()

    def _resize_image(self, event=None):
        if self._original_pil_image is None:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return  # Vermeidet width/height = 0 Fehler!

        resized_pil = resize_with_aspect_ratio(
            self._original_pil_image,
            canvas_width,
            canvas_height
        )
        
        self._image = ImageTk.PhotoImage(resized_pil)


        # === NEU: Maske synchron skalieren ===
        if self._original_mask_pil:
            resized_mask = resize_with_aspect_ratio(
                self._original_mask_pil,
                canvas_width,
                canvas_height
            )
            self._mask_overlay = ImageTk.PhotoImage(resized_mask)
        else:
            self._mask_overlay = None

        # === NEU: Berechne Scale & Offsets ===
        original_width, original_height = self._original_pil_image.size
        display_width, display_height = resized_pil.size

        self._scale_factor = display_width / original_width
        self._offset_x = (canvas_width - display_width) // 2
        self._offset_y = (canvas_height - display_height) // 2
        
        self.canvas.delete("all")
        self.canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            anchor="center",
            image=self._image
        )

        # Maske drüberlegen, wenn vorhanden
        if self._mask_overlay:
            self.canvas.create_image(
                canvas_width // 2,
                canvas_height // 2,
                anchor="center",
                image=self._mask_overlay
            )
        if self.boxes:
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

        box = {
            'annotation_type': self.annotation_type_state,
            'x1': int((min(self.start_x, x) - self._offset_x) / self._scale_factor),
            'y1': int((min(self.start_y, y) - self._offset_y) / self._scale_factor),
            'x2': int((max(self.start_x, x) - self._offset_x) / self._scale_factor),
            'y2': int((max(self.start_y, y) - self._offset_y) / self._scale_factor),
        }

        width = abs(box['x2'] - box['x1'])
        height = abs(box['y2'] - box['y1'])

        if width < 5 or height < 5:
            print("Ignored: too small to be a valid box.")
            return

        self.boxes.append(box)
        self.clear_boxes()
        self.display_boxes(self.boxes)

        self.start_x = None
        self.start_y = None
        self.current_box = None
        self.generate_mask_from_bbox()

    
    def display_boxes(self, boxes, color="green"):
        """Display a list of boxes (in original image coordinates)"""
        self.clear_boxes()

        for idx, box in enumerate(boxes):
            scaled_box = {
                'x1': box['x1'] * self._scale_factor + self._offset_x,
                'y1': box['y1'] * self._scale_factor + self._offset_y,
                'x2': box['x2'] * self._scale_factor + self._offset_x,
                'y2': box['y2'] * self._scale_factor + self._offset_y
            }
            rect_id = self.canvas.create_rectangle(
                scaled_box['x1'], scaled_box['y1'],
                scaled_box['x2'], scaled_box['y2'],
                outline="red" if self.selected_box_index is not None and idx == self.selected_box_index else color,
                fill="",  # oder transparente Fläche
                width=2
            )
            self.box_rects.append(rect_id)
            self.canvas.tag_bind(rect_id, "<Button-1>", lambda e, i=idx: self.select_box(i))

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

        print(f"Deleting box index {self.selected_box_index}")

        # Remove from list
        del self.boxes[self.selected_box_index]

        # Clear all old rectangles and redraw remaining boxes
        self.selected_box_index = None
        self.clear_boxes()
        self.display_boxes(self.boxes)

        print("Selected box deleted & display refreshed.")



       
    # def clear_boxes(self):
    #     """Clear all boxes from display"""
    #     self.boxes = []
    #     # Keep the image, delete everything else
    #     self.canvas.delete("all")
    #     if self._image:
    #         self.canvas.create_image(0, 0, anchor="nw", image=self._image)
    
    def clear_boxes(self):
        """Clear all boxes from display"""
        # Lösche alle Rechtecke aus Canvas
        for rect in self.box_rects:
            self.canvas.delete(rect)
        self.box_rects = []

        # Anzeige-Reset: Bild neu zeichnen
        self.canvas.delete("all")
        if self._image:
            self.canvas.create_image(
                self.canvas.winfo_width() // 2,
                self.canvas.winfo_height() // 2,
                anchor="center",
                image=self._image
            )


    def set_drawing_mode(self, enabled):
        """Enable or disable box drawing"""
        self.drawing = enabled
        
    def get_boxes(self):
        """Get list of boxes in original image coordinates"""
        return self.boxes
    


    def generate_mask_from_bbox(self):
        """Nimmt die erste BBox, generiert eine Maske, zeigt sie an & speichert sie."""
        if not self.boxes:
            print("No BBoxes available for segmentation!")
            return

        bbox = self.boxes[0]  # Beispiel: nur erste Box
        box = np.array([bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']])

        image_np = np.array(self._original_pil_image)

        # ⏩ 1) SAM aufrufen
        result_mask, details = segment(image_np, box)

        print("Segmentation done:", details)

         # 2) Erstelle farbiges RGBA-Overlay mit Transparenz
        h, w = result_mask.shape[:2]
        rgba_mask = np.zeros((h, w, 4), dtype=np.uint8)
        rgba_mask[..., :3] = [30, 144, 255]  # dein Blau-Ton in RGB
        rgba_mask[..., 3] = (result_mask > 0).astype(np.uint8) * 120  # Alpha-Kanal (0–255)

        # 3) Speichere Original-PIL Maske für späteres Resizing
        self._original_mask_pil = Image.fromarray(rgba_mask)

        # 4) Skaliere & zeige Maske im Canvas
        resized_mask = resize_with_aspect_ratio(
            self._original_mask_pil,
            self.canvas.winfo_width(),
            self.canvas.winfo_height()
        )
        self._mask_overlay = ImageTk.PhotoImage(resized_mask)

        self.canvas.create_image(
            self.canvas.winfo_width() // 2,
            self.canvas.winfo_height() // 2,
            anchor="center",
            image=self._mask_overlay
        )

        print("Segmentation done & mask displayed.")
