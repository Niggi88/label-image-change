import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from pathlib import Path
from utils import resize_with_aspect_ratio
from horizontal_spinner import HorizontalSpinner
# from image_cache import ImageCache
from image_annotation import ImageAnnotation
from annotatable_image import AnnotatableImage



class ImagePairList(list):
    def __init__(self, src):
        #                   /home/niklas/dataset/bildunterschied
        self.src = Path(src)
        self.images = sorted(self.src.glob("*.jpeg"), key=lambda file: int(file.name.split("-")[0]))
        assert len(self.images) > 0, f"no images found at {src}"
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
        
        
        # Create the pair viewer with required arguments
        self.pair_viewer = ImagePairViewer(self, "/home/niklas/dataset/bildunterschied/test_mini/complex")
        self.pair_viewer.pack(fill="both", expand=True)

        self.bind("<Escape>", lambda _: self.quit())
        # self.bind("<Right>", lambda _: self.pair_viewer.right())
        self.bind("<f>", lambda _: self.pair_viewer.right())
        # self.bind("<Left>", lambda _: self.pair_viewer.left())
        self.bind("<s>", lambda _: self.pair_viewer.left())
        self.bind("<a>", lambda _: self.pair_viewer.annotate_btn.invoke())
        self.bind("<n>", lambda _: self.pair_viewer.nothing_btn.invoke())


class ImagePairViewer(ttk.Frame):
    def __init__(self, container, base_src):
        print("init")
        super().__init__(container)
        src = "/home/niklas/dataset/bildunterschied/test_mini/clinical2"
        self.reset(src)

    def reset(self, src):
        # Create image pairs and annotation manager
        self.image_pairs = ImagePairList(src=src)
        self.annotations = ImageAnnotation(self.image_pairs.src)
        
        # Initialize state
        self.current_index = 0
        self.in_annotation_mode = False
        
        # Create image viewers
        self.image1 = AnnotatableImage(self)
        self.image1.grid(row=0, column=0, sticky="nsew")
        self.image2 = AnnotatableImage(self)
        self.image2.grid(row=0, column=1, sticky="nsew")
        
        # Create controls
        self.setup_controls()
        
        # Add horizontal spinner
        self.spinbox = HorizontalSpinner(self, self.image_pairs.ids(), self.set_images)
        self.spinbox.grid(row=2, column=0, columnspan=2)
        
        # Load first pair
        self.load_pair(0)
        print("loaded pair")
    
    def setup_controls(self):
        """Set up classification and navigation controls"""
        controls = ttk.Frame(self)
        controls.grid(row=1, column=0, columnspan=2, sticky="ew")
        
        # Classification buttons
        self.nothing_btn = ttk.Button(controls, text="Nothing Changed",
                                    command=lambda: self.classify("nothing"))
        self.nothing_btn.pack(side="left", fill="x", expand=True)
        
        self.reorder_btn = ttk.Button(controls, text="Reorder",
                                    command=lambda: self.classify("reorder"))
        self.reorder_btn.pack(side="left", fill="x", expand=True)
        
        self.annotate_btn = ttk.Button(controls, text="Annotate",
                                     command=self.toggle_annotation)
        self.annotate_btn.pack(side="left", fill="x", expand=True)
    
    def toggle_annotation(self):
        print("toggle annotation mode")
        """Toggle annotation mode on/off"""
        self.in_annotation_mode = not self.in_annotation_mode
        self.image1.set_drawing_mode(self.in_annotation_mode)
        self.image2.set_drawing_mode(self.in_annotation_mode)
        
        # Save current boxes if we're turning off annotation mode
        if not self.in_annotation_mode:
            self.save_current_boxes()
        
        # Update button state
        self.annotate_btn.state(['pressed'] if self.in_annotation_mode else ['!pressed'])
    
    def annotation_off(self):
        self.in_annotation_mode = False
        self.annotate_btn.state(['!pressed'])
        self.image1.set_drawing_mode(False)
        self.image2.set_drawing_mode(False)
        self.save_current_boxes()
        self.image1.clear_boxes()
        self.image2.clear_boxes()

    @property
    def current_id(self):
        im1_path, im2_path = self.image_pairs[self.current_index]
        return (im1_path, im2_path)# f"{im1_path.stem}_{im2_path.stem}"

    def save_current_boxes(self):
        """Save current boxes if any exist"""
        # boxes = self.image1.get_boxes() + self.image2.get_boxes()
        
        boxes = self.image2.get_boxes()
        if boxes:
            # add full id (img1_img2)
            self.annotations.save_pair_annotation(self.current_index, self.current_id, "annotate", boxes)
    
    def load_pair(self, index):
        """Load an image pair and its annotations"""
        print("load pair called")
        if self.in_annotation_mode:
            print("Was in annotation mode, toggling off")
            self.annotation_off()  # This will also save boxes

        if 0 <= index < len(self.image_pairs):
            # Save any current boxes before switching
            if self.in_annotation_mode:
                self.save_current_boxes()
            
            self.current_index = index
            img1, img2 = self.image_pairs[index]
            
            # Load images
            self.image1.load_image(img1)
            self.image2.load_image(img2)
            
            # Load any existing annotations
            annotation = self.annotations.get_pair_annotation(index)
            if annotation["type"] == "annotate":
                self.image1.display_boxes(annotation["boxes"], "red")
                self.image2.display_boxes(annotation["boxes"])
            
            self.update_ui_state(annotation["type"])
            
            
        if self.end_of_set:
            print("end of line")
    
    @property
    def end_of_set(self):
        return self.current_index == len(self.image_pairs) - 1

    def update_ui_state(self, annotation_type):
        """Update UI to reflect current annotation state"""
        # Reset all buttons
        for btn in [self.nothing_btn, self.reorder_btn, self.annotate_btn]:
            btn.state(['!pressed'])
        
        # Update button state
        if annotation_type == "nothing":
            self.nothing_btn.state(['pressed'])
        elif annotation_type == "reorder":
            self.reorder_btn.state(['pressed'])
        elif annotation_type == "annotate":
            self.annotate_btn.state(['pressed'])
            # Re-enable drawing if we were in annotation mode
            self.image1.set_drawing_mode(self.in_annotation_mode)
            self.image2.set_drawing_mode(self.in_annotation_mode)
    
    def classify(self, classification_type):
        """Save a simple classification and move to next pair"""
        self.annotations.save_pair_annotation(self.current_index, self.current_id, classification_type)
        self.right()
        # self.load_pair(self.current_index + 1)
    
    def left(self):
        ret = self.spinbox.animate_scroll(-1)

    def right(self):
        ret = self.spinbox.animate_scroll(+1)
        if ret == HorizontalSpinner.ReturnCode.END_RIGHT: 
            print("END_RIGHT")

    def set_images(self, idx):
        self.load_pair(idx)


app = PairViewerApp()


app.mainloop()