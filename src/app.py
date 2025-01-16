import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from pathlib import Path
from utils import resize_with_aspect_ratio
from horizontal_spinner import HorizontalSpinner
from image_cache import ImageCache


class ImagePairList(list):
    def __init__(self, src="/home/niklas/datasets/bildunterschied/8k-test/session_0cacfd77-09c9-42a4-839e-29e33981287d"):
        self.src = Path(src)
        self.images = sorted(self.src.glob("*.jpeg"), key=lambda file: int(file.name.split("-")[0]))
        self.image_pairs = list(zip(self.images[:-1], self.images[1:]))

    def __getitem__(self, index):
        # Allow indexing into image_pairs
        return self.image_pairs[index]
    
    def __iter__(self):
        return iter(self.image_pairs)
    
    def __len__(self):
        return len(self.image_pairs)
    
    def ids(self):
        return list(range(len(self)))


def open_image(image_dir):
    pil_img = Image.open(image_dir)
    pil_img = resize_with_aspect_ratio(pil_img, 1000, 1000)
    tk_image = ImageTk.PhotoImage(pil_img)
    return tk_image


class PairViewerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Side by Side Images")
        self.pair_viewer = PairViewer(self)
        self.pair_viewer.pack(fill="both", expand=True)

        self.bind("<Escape>", lambda _: app.quit())
        self.bind("<Right>", lambda _: app.pair_viewer.right())
        self.bind("<Left>", lambda _: app.pair_viewer.left())

class PairViewer(ttk.Frame):
    def __init__(self, container):
        super().__init__(container)
        self.image_sets = ImagePairList()
        self.image_cache = ImageCache()
        
        # Create persistent label widgets
        self.label1 = ttk.Label(self)
        self.label1.grid(row=0, column=0, sticky="EW")
        self.label2 = ttk.Label(self)
        self.label2.grid(row=0, column=1, sticky="EW")
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        set1 = self.image_sets[0]
        img1, img2 = set1
        self.photoimage1 = open_image(img1)
        self.photoimage2 = open_image(img2)
        self.reload_images()

        self.spinbox = HorizontalSpinner(self, self.image_sets.ids(), self.set_images)
        self.spinbox.grid(row=1, column=0, columnspan=2)

        # buttons
        self.nothing = ttk.Button(self, text="nothing", command=self.classify_nothing)
        self.nothing.grid(row=2, column=0, sticky="EW")

        self.reorder = ttk.Button(self, text="reorder", command=self.classify_reorder)
        self.reorder.grid(row=2, column=1, sticky="EW")

        self.new_product = ttk.Button(self, text="new product", command=self.classify_reorder)
        self.new_product.grid(row=2, column=2, sticky="EW")

    def classify_nothing(self):
        print("classified as nothing")

    def classify_reorder(self):
        print("classified as nothing")

    def classify_new_product(self):
        print("classified as nothing")

    def set_images(self, idx):
        set1 = self.image_sets[idx]
        img1, img2 = set1
        
        # Try cache first
        self.photoimage1 = self.image_cache.get(img1)
        self.photoimage2 = self.image_cache.get(img2)
        
        # Load if not in cache
        if self.photoimage1 is None:
            self.photoimage1 = open_image(img1)
            self.image_cache.add(img1, self.photoimage1)
        if self.photoimage2 is None:
            self.photoimage2 = open_image(img2)
            self.image_cache.add(img2, self.photoimage2)
        
        # Preload next and previous pairs
        next_idx = idx + 1
        prev_idx = idx - 1
        preload_paths = []
        if next_idx < len(self.image_sets):
            preload_paths.extend(self.image_sets[next_idx])
        if prev_idx >= 0:
            preload_paths.extend(self.image_sets[prev_idx])
        
        # Just call preload_images directly - it handles the image processing internally
        self.image_cache.preload_images(preload_paths)
        
        self.reload_images()

    def reload_images(self):
        self.label1.configure(image=self.photoimage1)
        self.label2.configure(image=self.photoimage2)

    def left(self):
        self.spinbox.animate_scroll(-1)

    def right(self):
        self.spinbox.animate_scroll(+1)

    def increment_spinbox(self, event):
        """Increment the Spinbox value."""
        current_value = self.spinbox.get()
        if current_value.isdigit():
            index = self.image_sets.index(int(current_value))
            if index < len(self.image_sets) - 1:
                self.spinbox.set(self.image_sets[index + 1])

    def decrement_spinbox(self, event):
        """Decrement the Spinbox value."""
        current_value = self.spinbox.get()
        if current_value.isdigit():
            index = self.image_sets.index(int(current_value))
            if index > 0:
                self.spinbox.set(self.image_sets[index - 1])

    def switch_image(self):
        value = self.spinbox.get()
        print(f"Selected value: {value}")


app = PairViewerApp()


app.mainloop()