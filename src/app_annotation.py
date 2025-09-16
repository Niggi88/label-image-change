import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from pathlib import Path
from utils import resize_with_aspect_ratio, flush_annotation_cache
from horizontal_spinner import HorizontalSpinner
# from image_cache import ImageCache
from image_annotation import ImageAnnotation
from annotatable_image import AnnotatableImage
import tkinter.messagebox as messagebox
from config import *
from pathlib import Path
import base64
import io
import copy
import json
import requests
import threading  # ensure this import exists at top of file
import time
import os
from urllib.parse import urlparse, urljoin
from ui_styles import init_ttk_styles

# from loader import ImagePairList
from viewer import ImagePairViewer




class PairViewerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        init_ttk_styles(self) 

        from tkinter import font

        self.tk.call('tk', 'scaling', UI_SCALING)

        self.title("Side by Side Images")
        
        default_font = font.nametofont("TkDefaultFont")

        default_font.configure(size=int(default_font['size'] * FONT_SCALING))

            # Create the pair viewer with required arguments
        self.pair_viewer = ImagePairViewer(self, DATASET_DIR)
            
        self.pair_viewer.pack(fill="both", expand=True)






if __name__ == "__main__":
    app = PairViewerApp()
    app.mainloop()