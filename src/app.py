import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from pathlib import Path
from utils import resize_with_aspect_ratio
from horizontal_spinner import HorizontalSpinner
# from image_cache import ImageCache
from image_annotation import ImageAnnotation
from annotatable_image import AnnotatableImage
import tkinter.messagebox as messagebox
from config import *
from pathlib import Path
import base64
import io


# TODO: removed
# TODO: new class / no class
# TODO: add x als gelöscht


class ImagePairList(list):
    def __init__(self, src):
        #                   /home/niklas/dataset/bildunterschied
        self.src = Path(src)
        # self.parent = parent
        # self.annotation_controller = annotation_controller
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


# def open_image(image_dir):
#     pil_img = Image.open(image_dir)
#     print("pil_img", pil_img)
#     pil_img = resize_with_aspect_ratio(pil_img, 50, 50)
#     print("pil_img", pil_img)
#     tk_image = ImageTk.PhotoImage(pil_img)
#     return tk_image


class PairViewerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Side by Side Images")
        
        
        # Create the pair viewer with required arguments
        self.pair_viewer = ImagePairViewer(self, DATASET_DIR)
        self.pair_viewer.pack(fill="both", expand=True)

        self.bind("<Escape>", lambda _: self.quit())
        # self.bind("<f>", lambda _: self.pair_viewer.right())
        self.bind("<f>", lambda _: self.pair_viewer.nothing_btn.invoke())
        # self.bind("<s>", lambda _: self.pair_viewer.left())
        self.bind("<s>", lambda _: self.pair_viewer.left())

        self.bind("<a>", lambda _: self.pair_viewer.annotate_btn.invoke())
        self.bind("<n>", lambda _: self.pair_viewer.nothing_btn.invoke())
        self.bind("<c>", lambda _: self.pair_viewer.chaos_btn.invoke())


class ImagePairViewer(ttk.Frame):
    def __init__(self, container, base_src):
        print("init")
        super().__init__(container)
        # Grid-Spalten und Zeilen definieren, damit sie Platz fair teilen:
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.sessions = Path(base_src).glob("*")
        # src = "/home/niklas/dataset/bildunterschied/test_mini/clinical2"
        # self.reset(src)
        self.reset(next(self.sessions))
        self.selected_box_index = None
    def reset(self, src):
        self.after(100, self.show_reset_message)
        # Create image pairs and annotation manager
        self.image_pairs = ImagePairList(src=src)
        self.annotations = ImageAnnotation(self.image_pairs.src)
        
        # Initialize state
        self.current_index = 0
        self.in_annotation_mode = False
        
        # Create image viewers
        self.image1 = AnnotatableImage(self, annotation_controller=self.annotations, controller=self)
        self.image1.grid(row=0, column=0, sticky="nsew")
        self.image2 = AnnotatableImage(self, annotation_controller=self.annotations, controller=self)
        self.image2.grid(row=0, column=1, sticky="nsew")
        
        # Create controls
        self.setup_controls()
        
        # Add horizontal spinner
        self.spinbox = HorizontalSpinner(self, self.image_pairs.ids(), self.set_images)
        self.spinbox.grid(row=2, column=0, columnspan=2)
        
        # Load first pair
        self.load_pair(0)
        print("loaded pair")

    def show_reset_message(self):
        dialog = tk.Toplevel(self)
        dialog.title("Reset Complete")
        label = tk.Label(dialog, text="Application has been reset successfully", padx=20, pady=20)
        label.pack()
        dialog.bind("<KeyPress>", lambda e: dialog.destroy())
        dialog.focus_set()  # This is critical - gives keyboard focus to the dialog

    def setup_controls(self):
        """Set up classification and navigation controls"""
        controls = ttk.Frame(self)
        controls.grid(row=1, column=0, columnspan=2, sticky="ew")
        
        self.nothing_btn = ttk.Button(controls, text="Nothing Changed", 
                                    command=lambda: self.before_action(ImageAnnotation.Classes.NOTHING))
        self.chaos_btn = ttk.Button(controls, text="Chaos", 
                                    command=lambda: self.before_action(ImageAnnotation.Classes.CHAOS))
        self.annotate_btn = ttk.Button(controls, text="Annotate", 
                                    command=lambda: self.before_action(ImageAnnotation.Classes.ANNOTATION))
        self.clear_btn = ttk.Button(
            controls,
            text="Clear All",
            command=self.clear_current_boxes
        )
        self.delete_selected_btn = ttk.Button(
            controls,
            text="Delete Selected Box",
            command=self.before_delete_selected  # ACHTUNG: gleich neue Methode
        )

        self.nothing_btn.pack(side="left", fill="x", expand=True)
        self.chaos_btn.pack(side="left", fill="x", expand=True)
        self.annotate_btn.pack(side="left", fill="x", expand=True)
        self.delete_selected_btn.pack(side="left", fill="x", expand=True)
        self.clear_btn.pack(side="left", fill="x", expand=True)

        # ⏺️ Speichere Buttons in Liste (außer Clear!)
        self.buttons = [
            self.nothing_btn,
            self.chaos_btn,
            self.annotate_btn,
            self.delete_selected_btn
        ]

    
    def reset_buttons(self):
        """Setzt alle Buttons in unpressed"""
        for btn in self.buttons:
            btn.state(['!pressed'])

    def before_delete_selected(self):
        self.reset_buttons()
        self.toggle_annotation(False)
        self.delete_selected_btn.state(['pressed'])

        # Frage BEIDE Bilder, ob eine Box ausgewählt ist:
        if self.image1.selected_box_index is not None:
            self.image1.delete_selected_box()
        elif self.image2.selected_box_index is not None:
            self.image2.delete_selected_box()
        else:
            print("No box selected in either image.")

        # Speichern nach Löschung – IMMER für beide Seiten!
        self.annotations.save_pair_annotation(
            self.current_index,
            self.current_id,
            ImageAnnotation.Classes.ANNOTATION,
            self.image1.get_boxes() + self.image2.get_boxes()
        )

        self.delete_selected_btn.state(['!pressed'])



    def clear_current_boxes(self):
        """Clear all boxes for the current image pair and update JSON"""
        print(f"Clearing boxes for pair {self.current_index}")

        # Anzeige leeren
        self.image1.clear_boxes()
        self.image2.clear_boxes()

        # Daten leeren
        self.image1.boxes = []
        self.image2.boxes = []

        # Auch in der Annotation leeren & speichern
        self.annotations.save_pair_annotation(
            self.current_index,
            self.current_id,
            ImageAnnotation.Classes.ANNOTATION,  # Typ bleibt Annotation, nur ohne Boxen
            []
        )

        print(f"Boxes cleared for pair {self.current_index}")

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
        other_image = self.controller.image2 if self is self.controller.image1 else self.controller.image1
        other_image.boxes = [b for b in other_image.boxes if b.get('pair_id') != pair_id]

        # Clear & redraw
        self.clear_boxes()
        self.display_boxes(self.boxes)

        other_image.clear_boxes()
        other_image.display_boxes(other_image.boxes)

        self.selected_box_index = None
        other_image.selected_box_index = None
        print("Deleted box in both images.")



    def before_action(self, button_id):
        self.reset_buttons()
        self.state = button_id

        if button_id == ImageAnnotation.Classes.ANNOTATION:
            self.annotate_btn.state(['pressed'])
            self.toggle_annotation(True)
        else:
            self.toggle_annotation(False)
            if button_id == ImageAnnotation.Classes.NOTHING:
                self.nothing_btn.state(['pressed'])
            elif button_id == ImageAnnotation.Classes.CHAOS:
                self.chaos_btn.state(['pressed'])

        self.process_action()
        self.annotations.save_pair_annotation(
            self.current_index, self.current_id, self.state, self.image2.get_boxes()
        )

        if not self.state == ImageAnnotation.Classes.ANNOTATION:
            self.right()


    def process_action(self):
        print("State was set to:", self.state)
    
    def classify(self, classification_type):
        """Save a simple classification and move to next pair"""
        self.annotations.save_pair_annotation(self.current_index, self.current_id, classification_type)
        self.right()
        # self.load_pair(self.current_index + 1)
    
    def toggle_annotation(self, enabled=None):
        """Schalte Annotation Mode gezielt an/aus"""
        if enabled is None:
            self.in_annotation_mode = not self.in_annotation_mode
        else:
            self.in_annotation_mode = enabled

        self.image1.set_drawing_mode(self.in_annotation_mode)
        self.image2.set_drawing_mode(self.in_annotation_mode)

        if not self.in_annotation_mode:
            self.save_current_boxes()

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
            print("saving boxes", boxes)
            self.annotations.save_pair_annotation(self.current_index, self.current_id, ImageAnnotation.Classes.ANNOTATION, boxes)
            
        anti_boxes = self.image1.get_boxes()
        if anti_boxes:
            print("saving anti boxes", anti_boxes)
            self.annotations.save_pair_annotation(self.current_index, self.current_id, ImageAnnotation.Classes.ANNOTATION_X, anti_boxes)
   
    
    def load_pair(self, index):
        print("load pair called")
        if self.in_annotation_mode:
            print("Was in annotation mode, toggling off")
            self.annotation_off()

        if 0 <= index < len(self.image_pairs):
            self.current_index = index
            img1, img2 = self.image_pairs[index]

            # 1) Alles leeren
            self.image1.clear_all()            
            self.image2.clear_all()

            self.image1._resize_image()
            self.image2._resize_image()

            # 2) Bilder neu laden
            self.image1.load_image(img1)
            self.image2.load_image(img2)

            # 3) Annotation laden
            annotation = self.annotations.get_pair_annotation(index)
            print("annotation TYPE:", annotation["type"])
            print("===", annotation)
            print("ImageAnnotation.Classes.ANNOTATION:", ImageAnnotation.Classes.ANNOTATION)

            if annotation["type"] == ImageAnnotation.Classes.ANNOTATION:
                boxes = annotation["boxes"]
                print("this are the boxes values in load_pair: ", boxes)
                # 3a) Speichere sie intern
                self.image1.boxes = boxes
                self.image2.boxes = boxes

                # 3b) Zeige sie an
                self.image1.display_boxes(boxes)
                self.image2.display_boxes(boxes)

                self.image1._original_mask_pils = []
                self.image2._original_mask_pils = []

                for box in boxes:
                    if "mask_base64" in box and "mask_image_id" in box:
                        mask_bytes = base64.b64decode(box["mask_base64"])
                        mask_pil = Image.open(io.BytesIO(mask_bytes)).convert("RGBA")
                        if box["mask_image_id"] == str(self.image1.image_path):
                            self.image1._original_mask_pils.append(mask_pil)
                        elif box["mask_image_id"] == str(self.image2.image_path):
                            self.image2._original_mask_pils.append(mask_pil)

                
                self.image1.display_mask()
                self.image2.display_mask()

            self.update_ui_state(annotation["type"])

        if self.end_of_set:
            print("end of line")



    # def load_pair(self, index):
    #     print("load pair called")
    #     if self.in_annotation_mode:
    #         print("Was in annotation mode, toggling off")
    #         self.annotation_off()

    #     if 0 <= index < len(self.image_pairs):
    #         self.current_index = index
    #         img1, img2 = self.image_pairs[index]

    #         self.image1.clear_boxes()
    #         self.image2.clear_boxes()
    #         self.image1.boxes = []
    #         self.image2.boxes = []


    #         annotation = self.annotations.get_pair_annotation(index)
    #         boxes = annotation["boxes"] if annotation["type"] == ImageAnnotation.Classes.ANNOTATION else []
    #         print("boxes from load_pair:", boxes)
    #         self.image1.load_image(img1, boxes)
    #         self.image2.load_image(img2, boxes)

    #         if annotation["type"] == ImageAnnotation.Classes.ANNOTATION and annotation["boxes"]:
    #             self.image1.boxes = annotation["boxes"]
    #             self.image2.boxes = annotation["boxes"]
    #             self.image1.display_boxes(annotation["boxes"], "green")
    #             self.image2.display_boxes(annotation["boxes"], "green")
    #         else:
    #             # Keine Boxen vorhanden: sicher clear
    #             self.image1.clear_boxes()
    #             self.image2.clear_boxes()

    #         self.update_ui_state(annotation["type"])

    #     if self.end_of_set:
    #         print("end of line")


    @property
    def end_of_set(self):
        return self.current_index == len(self.image_pairs) - 1

    def update_ui_state(self, annotation_type):
        """Update UI to reflect current annotation state"""
        # Reset all buttons
        for btn in [self.nothing_btn, self.chaos_btn, self.annotate_btn]:
            btn.state(['!pressed'])
        
        # Update button state
        if annotation_type == ImageAnnotation.Classes.NOTHING:
            self.nothing_btn.state(['pressed'])
        elif annotation_type == ImageAnnotation.Classes.CHAOS:
            self.chaos_btn.state(['pressed'])
        elif annotation_type == ImageAnnotation.Classes.ANNOTATION:
            self.annotate_btn.state(['pressed'])
            # Re-enable drawing if we were in annotation mode
            self.image1.set_drawing_mode(self.in_annotation_mode)
            self.image2.set_drawing_mode(self.in_annotation_mode)
    
    def left(self):
        ret = self.spinbox.animate_scroll(-1)

    def right(self):
        if len(self.image2.get_boxes()) == 0: print("empty")
        else: print("full")
        ret = self.spinbox.animate_scroll(+1)
        if ret == HorizontalSpinner.ReturnCode.END_RIGHT: 
            try:
                next_session = next(self.sessions)
                print(next_session)
                self.reset(next_session)
            except:
                print("done")
                self.quit()

    def set_images(self, idx):
        self.load_pair(idx)


app = PairViewerApp()


app.mainloop()