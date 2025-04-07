import tkinter as tk
from tkinter import ttk

from utils import resize_with_aspect_ratio
from PIL import Image, ImageTk


class AnnotatableImage(ttk.Frame):
    """A widget that can display an image and its annotations"""
    def __init__(self, container):
        super().__init__(container)
        self.canvas = tk.Canvas(self)
        self.canvas.pack(fill="both", expand=True)
        
        # Drawing state
        self.drawing = False
        self.start_x = None
        self.start_y = None
        self.current_box = None
        self.boxes = []
        
        # Bind mouse events for drawing
        self.canvas.bind('<Button-1>', self.start_box)
        self.canvas.bind('<B1-Motion>', self.draw_box)
        self.canvas.bind('<ButtonRelease-1>', self.end_box)
        
        self._image = None  # Keep reference to avoid garbage collection
        self._scale_factor = 1.0
    
    def load_image(self, image_path, max_size=(1000, 1000)):
        """Load and display an image using existing resize method"""
        print("loaded image", image_path)
        pil_image = Image.open(image_path)
        
        # Store original size for scaling factor calculation
        original_size = pil_image.size
        
        # Use existing resize method
        pil_image = resize_with_aspect_ratio(pil_image, 1000, 1000)
        self._image = ImageTk.PhotoImage(pil_image)
        
        # Calculate scale factor based on the resize results
        self._scale_factor = pil_image.size[0] / original_size[0]
        
        # Update canvas size and display image
        self.canvas.config(width=pil_image.size[0], height=pil_image.size[1])
        self.canvas.create_image(0, 0, anchor="nw", image=self._image)


    def _calculate_scaled_size(self, size, max_size):
        """Calculate new size maintaining aspect ratio"""
        ratio = min(max_size[0] / size[0], max_size[1] / size[1])
        return (int(size[0] * ratio), int(size[1] * ratio))
    
    def start_box(self, event):
        if not self.drawing:
            return
        self.start_x = event.x
        self.start_y = event.y
    
    def draw_box(self, event):
        if not self.drawing or not self.start_x:
            return
        if self.current_box:
            self.canvas.delete(self.current_box)
        self.current_box = self.canvas.create_rectangle(
            self.start_x, self.start_y,
            event.x, event.y,
            outline='blue'
        )
    
    def end_box(self, event):
        if not self.drawing or not self.start_x:
            return
        # Store in original image coordinates
        box = {
            'x1': int(min(self.start_x, event.x) / self._scale_factor),
            'y1': int(min(self.start_y, event.y) / self._scale_factor),
            'x2': int(max(self.start_x, event.x) / self._scale_factor),
            'y2': int(max(self.start_y, event.y) / self._scale_factor),
        }
        self.boxes.append(box)
        self.start_x = None
        self.start_y = None
    
    def display_boxes(self, boxes, color="green"):
        """Display a list of boxes (in original image coordinates)"""
        self.clear_boxes()
        for box in boxes:
            scaled_box = {
                'x1': box['x1'] * self._scale_factor,
                'y1': box['y1'] * self._scale_factor,
                'x2': box['x2'] * self._scale_factor,
                'y2': box['y2'] * self._scale_factor
            }
            self.canvas.create_rectangle(
                scaled_box['x1'], scaled_box['y1'],
                scaled_box['x2'], scaled_box['y2'],
                outline=color
            )
    
    def clear_boxes(self):
        """Clear all boxes from display"""
        self.boxes = []
        # Keep the image, delete everything else
        self.canvas.delete("all")
        if self._image:
            self.canvas.create_image(0, 0, anchor="nw", image=self._image)
    
    def set_drawing_mode(self, enabled):
        """Enable or disable box drawing"""
        self.drawing = enabled
        
    def get_boxes(self):
        """Get list of boxes in original image coordinates"""
        return self.boxes