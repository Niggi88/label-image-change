from pathlib import Path
import json
from config import *

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app import ImagePairViewer
    from image_annotation import ImageAnnotation

class ImageAnnotation:
    class Classes:
        ANNOTATION = "annotation"
        ANNOTATION_X = "annotation_xy"
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
    
    def save_pair_annotation(self, image1, image2, annotation_type, boxes=None):
        from annotatable_image import mask_pil_to_base64

        # Entscheide, welche Boxen du speichern willst
        if boxes:
            boxes1 = boxes
            boxes2 = boxes
            annotation_type = ImageAnnotation.Classes.ANNOTATION
        else:
            boxes1 = image1.get_boxes()
            boxes2 = image2.get_boxes()
            if not boxes1 and not boxes2:
                annotation_type = ImageAnnotation.Classes.NOTHING

        pair_id = image1.controller.current_index


        self.annotations[f"{pair_id}"] = {
            "type": annotation_type,
            "im1_path": str(image1.image_path),
            "im2_path": str(image2.image_path),
            "boxes1": boxes1,
            "boxes2": boxes2,
            "masks1": [
                mask_pil_to_base64(mask) for mask in image1._original_mask_pils
            ],
            "masks2": [
                mask_pil_to_base64(mask) for mask in image2._original_mask_pils
            ],
            "image1_size": image1.image_size,
            "image2_size": image2.image_size
        }
        self.save_annotations()
        print(f"[SAVE] Pair {pair_id} -> boxes1: {len(boxes1)}, boxes2: {len(boxes2)}")
        print(json.dumps(self.annotations[f"{pair_id}"], indent=2))
