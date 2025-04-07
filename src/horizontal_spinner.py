import tkinter as tk
from tkinter import ttk
import math

class HorizontalSpinner(tk.Frame):
    class ReturnCode:
        NORMAL = 0
        ANIMATION_IN_PROGRESS = -1
        END_RIGHT = -2
        END_LEFT = -3

    def __init__(self, master, items, on_change=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.items = items
        self.current_index = 0
        self.animation_in_progress = False
        self.on_change = on_change
        
        # Create a canvas for the spinner
        self.canvas = tk.Canvas(self, height=50, width=300, bg=self.cget('bg'))
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Add navigation buttons
        self.prev_button = ttk.Button(self, text="◀", command=self.scroll_left)
        self.prev_button.pack(side="left")
        
        self.next_button = ttk.Button(self, text="▶", command=self.scroll_right)
        self.next_button.pack(side="right")
        
        # Initialize visible items (show 5 items at a time)
        self.visible_count = 5
        self.item_width = 60
        self.center_x = self.canvas.winfo_reqwidth() / 2
        
        # Draw the initial state
        self.draw_items()
        
        # Bind resize event
        self.canvas.bind('<Configure>', self.on_resize)

    def on_resize(self, event):
        self.center_x = event.width / 2
        self.draw_items()

    def draw_items(self):
        self.canvas.delete("all")
        
        # Calculate the range of visible items
        start_idx = max(0, self.current_index - self.visible_count // 2)
        end_idx = min(len(self.items), start_idx + self.visible_count)
        
        # Adjust start_idx if we're near the end
        if end_idx - start_idx < self.visible_count and start_idx > 0:
            start_idx = max(0, end_idx - self.visible_count)
        
        for i in range(start_idx, end_idx):
            # Calculate position and scale based on distance from center
            distance_from_center = i - self.current_index
            x = self.center_x + (distance_from_center * self.item_width)
            
            # Scale and opacity based on distance
            scale = 1 - abs(distance_from_center) * 0.15
            opacity = 1 - abs(distance_from_center) * 0.2
            
            # Convert opacity to hex color (ensuring 6 digits)
            opacity_hex = int(opacity * 255)
            color = f"#{opacity_hex:02x}{opacity_hex:02x}{opacity_hex:02x}"
            
            # Calculate font size
            base_font_size = 14
            scaled_font_size = int(base_font_size * scale)
            
            # Create custom font for the scaled size
            font = ("Arial", scaled_font_size, "bold")
            
            # Draw the number
            self.canvas.create_text(
                x, 25,
                text=str(self.items[i]),
                fill=color,
                font=font,
                tags=f"item_{i}"
            )

    def animate_scroll(self, direction):
        print("in animate scroll", direction)
        if self.animation_in_progress:
            return self.ReturnCode.ANIMATION_IN_PROGRESS
        
        next_index = self.current_index + direction
        if not (0 <= next_index < len(self.items)):
            print(next_index)
            if next_index < 0: return self.ReturnCode.END_LEFT
            if len(self.items) <= next_index: return self.ReturnCode.END_RIGHT
            
        self.animation_in_progress = True
        steps = 5
        dx = -self.item_width / steps * direction
        
        # Immediately update the current index and trigger callback
        self.current_index = next_index
        if self.on_change:
            self.on_change(self.items[self.current_index])
        
        def animate_step(remaining_steps, total_dx):
            if remaining_steps <= 0:
                self.draw_items()
                self.animation_in_progress = False
                return
            
            self.canvas.move("all", dx, 0)
            self.after(20, lambda: animate_step(remaining_steps - 1, total_dx + dx))
        
        # Start animation in background
        self.after(0, lambda: animate_step(steps, 0))
        return self.ReturnCode.NORMAL

    def scroll_left(self, event=None):
        if self.current_index > 0 and not self.animation_in_progress:
            self.animate_scroll(-1)

    def scroll_right(self, event=None):
        if self.current_index < len(self.items) - 1 and not self.animation_in_progress:
            self.animate_scroll(1)

    def get(self):
        return str(self.items[self.current_index])