from pathlib import Path
import json


class ImageAnnotation:
    """Handles loading, saving, and managing annotations for image pairs"""
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.annotations_file = self.base_path / "annotations.json"
        self.annotations = self._load_annotations()
    
    def _load_annotations(self):
        if self.annotations_file.exists():
            with open(self.annotations_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_annotations(self):
        with open(self.annotations_file, 'w') as f:
            json.dump(self.annotations, f, indent=2)
    
    def get_pair_annotation(self, pair_id):
        return self.annotations.get(f"pair_{pair_id}", {
            "type": None,
            "boxes": []
        })
    
    def save_pair_annotation(self, pair_id, annotation_type, boxes=None):
        if boxes is None:
            boxes = []
        self.annotations[f"pair_{pair_id}"] = {
            "type": annotation_type,
            "boxes": boxes
        }
        self.save_annotations()