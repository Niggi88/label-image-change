from pathlib import Path
import json
from config import *

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app import ImagePairViewer
    from image_annotation import ImageAnnotation

class ImageAnnotation:
    class Classes:
        ANNOTATED = "annotated"
        SKIPPED = "skipped"
        NOTHING = "nothing"
        CHAOS = "chaos"

        # Jetzt als dicts:
        PAIR_STATES = {ANNOTATED, SKIPPED, NOTHING, CHAOS}

        ANNOTATION = "annotation"
        ANNOTATION_X = "annotation_xy"
        BOX_ANNOTATION_TYPES = {ANNOTATION, ANNOTATION_X}

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
            "pair_state": None,
            "boxes": []
        })
    
    # def save_pair_annotation(self, image1, image2, annotation_type, boxes=None):
    #     from annotatable_image import mask_pil_to_base64

    #     pair_id = image1.controller.current_index
    #     print("[DEBUG] Saving annotation with:")
    #     print(" - pair_id:", pair_id)
    #     print(" - image1:", getattr(image1, 'image_path', None))
    #     print(" - image2:", getattr(image2, 'image_path', None))
    #     print(" - type:", annotation_type)

    #     boxes1 = image1.get_boxes()
    #     boxes2 = image2.get_boxes()

    #     self.annotations[f"{pair_id}"] = {
    #         "type": annotation_type,
    #         "im1_path": str(image1.image_path),
    #         "im2_path": str(image2.image_path),
    #         "boxes1": boxes1,
    #         "boxes2": boxes2,
    #         "masks1": [
    #             mask_pil_to_base64(mask) for mask in image1._original_mask_pils
    #         ],
    #         "masks2": [
    #             mask_pil_to_base64(mask) for mask in image2._original_mask_pils
    #         ],
    #         "image1_size": image1.image_size,
    #         "image2_size": image2.image_size
    #     }

    #     self.save_annotations()
    #     print(f"[SAVE] Pair {pair_id} -> boxes1: {len(boxes1)}, boxes2: {len(boxes2)}")
    #     print("[DEBUG] self.annotations: ")
    #     print(json.dumps(self.annotations[f"{pair_id}"], indent=2))

    def save_pair_annotation(self, image1, image2, pair_state, boxes=None):
        pair_id = str(image1.controller.current_index)
        print("[DEBUG] Saving annotation for pair_id:", pair_id)

        boxes1 = image1.get_boxes()
        boxes2 = image2.get_boxes()
        print(f"[DEBUG] image1 boxes: {len(boxes1)} | image2 boxes: {len(boxes2)}")

        collected_boxes = boxes1 + boxes2

        final_boxes = []
        for box in collected_boxes:
            entry = {
                "x1": box["x1"],
                "y1": box["y1"],
                "x2": box["x2"],
                "y2": box["y2"],
                "annotation_type": box["annotation_type"],
                "pair_id": box.get("pair_id")
            }
            if "mask_base64" in box:
                entry["mask_base64"] = box["mask_base64"]
                entry["mask_image_id"] = box.get("mask_image_id")

            final_boxes.append(entry)

        self.annotations[f"{pair_id}"] = {
            "pair_state": pair_state,
            "im1_path": str(image1.image_path),
            "im2_path": str(image2.image_path),
            "image1_size": image1.image_size,
            "image2_size": image2.image_size,
            "boxes": final_boxes
        }

        self.save_annotations()
        print(f"[SAVE] Pair {pair_id} saved with {len(final_boxes)} boxes.")

