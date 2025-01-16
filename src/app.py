import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from pathlib import Path
from utils import resize_with_aspect_ratio


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





def open_image(image_dir):
    pil_img = Image.open(image_dir)
    pil_img = resize_with_aspect_ratio(pil_img, 600, 600)
    tk_image = ImageTk.PhotoImage(pil_img)
    return tk_image


class PairViewerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Side by Side Images")
        PairViewer(self).pack(fill="both", expand=True)

class PairViewer(ttk.Frame):
    def __init__(self, container):
        super().__init__(container)
        image_sets = ImagePairList()
        set1 = image_sets[0]
        img1, img2 = set1

        self.photoimage1 = open_image(img1)
        image1 = ttk.Label(self, image=self.photoimage1)
        image1.grid(row=0, column=0)

        self.photoimage2 = open_image(img2)
        image2 = ttk.Label(self, image=self.photoimage2)
        image2.grid(row=0, column=1)


app = PairViewerApp()
app.bind("<Escape>", lambda _: app.quit())

app.mainloop()