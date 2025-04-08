from pathlib import Path
import json
from config import *


class ImageAnnotation:
    class Classes:
        ANNOTATION = "annotation"
        NOTHING = "nothing"
        CHAOS = "reorder"
        OTHER = "other"

    """Handles loading, saving, and managing annotations for image pairs"""
    def __init__(self, base_path):

        self.reset(base_path)
    
    def reset(self, base_path):
        self.base_path = Path(base_path)
        self.annotations_file = self.base_path / "annotations.json"
        
        print("Annotations saved at", self.annotations_file)
        self.annotations = self._load_annotations() if CACHE else {}

    def _load_annotations(self):
        if self.annotations_file.exists():
            with open(self.annotations_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_annotations(self):
        with open(self.annotations_file, 'w') as f:
            json.dump(self.annotations, f, indent=2)
    
    def get_pair_annotation(self, pair_id):
        return self.annotations.get(f"{pair_id}", {
            "type": None,
            "current_id": None,
            "boxes": []
        })
    
    def save_pair_annotation(self, pair_id, images, annotation_type, boxes=None):
        if boxes is None:
            boxes = []
            
        if len(boxes) == 0 and annotation_type == ImageAnnotation.Classes.NOTHING: 
            annotation_type = ImageAnnotation.Classes.NOTHING
        im1, im2 = images
        self.annotations[f"{pair_id}"] = {
            "type": annotation_type,
            "im1": str(im1),
            "im2": str(im2),
            "boxes": boxes
        }
        self.save_annotations()