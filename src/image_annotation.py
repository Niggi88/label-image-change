from pathlib import Path
import json
from config import *
import os
from typing import TYPE_CHECKING
from datetime import datetime
from utils import report_annotation, already_annotated_on_server

if TYPE_CHECKING:
    from app import ImagePairViewer
    from image_annotation import ImageAnnotation



def make_relative_path(abs_path):
    """Convert an absolute image path to POSIX-style relative based on the dataset root"""
    return Path(abs_path).resolve().relative_to(Path(DATASET_DIR).resolve()).as_posix()


def make_absolute_path(relative_path, annotations_meta):
    """Reconstruct absolute path from POSIX-style relative path and meta root"""
    root = Path(annotations_meta.get("root", DATASET_DIR)).as_posix()
    return (root / Path(relative_path)).resolve()



class ImageAnnotation:
    class Classes:
        ANNOTATED = "annotated"
        NO_ANNOTATION = "no_annotation"
        NOTHING = "nothing"
        CHAOS = "chaos"

        # Jetzt als dicts:
        PAIR_STATES = {ANNOTATED, NO_ANNOTATION, NOTHING, CHAOS}

        ANNOTATION = "item_added"
        ANNOTATION_X = "item_removed"
        BOX_ANNOTATION_TYPES = {ANNOTATION, ANNOTATION_X}
        PAIR_STATE_COLORS = {
            NOTHING: "#ADD8E6",         # hellblau
            CHAOS: "#FFD700",          # gelb
            NO_ANNOTATION: "#B497B8",  # grau
            ANNOTATED: None            # keine Outline
        }

        HOVER_COLORS = {
            NOTHING: "#0000FF",         # real blue
            CHAOS: "#FFA500",           # orange
            NO_ANNOTATION: "#333333",   # dark grey
        }
    """Handles loading, saving, and managing annotations for image pairs"""
    def __init__(self, base_path, total_pairs=None):
        self.annotations_file = base_path
        self.annotations = {}
        self.total_pairs = total_pairs  # 👈 THIS LINE IS CRITICAL
        self.reset(base_path)
    
    def reset(self, base_path):
        self.base_path = Path(base_path)
        self.annotations_file = self.base_path / "annotations.json"
        print("🔁 [ImageAnnotation] Set annotation file to", self.annotations_file)
        
        print("Annotations saved at", self.annotations_file)
        self.annotations = self._load_annotations() if CACHE else {}

    def _load_annotations(self):
        if self.annotations_file.exists():
            with open(self.annotations_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_annotations(self):

        annotated_pairs = [
            key for key in self.annotations
            if key != "_meta" and self.annotations[key].get("pair_state") is not None
        ]

        total_pairs = self.total_pairs

        if len(annotated_pairs) == total_pairs:
            self.annotations["_meta"] = {
                "completed": True,
                "timestamp": datetime.now().isoformat(),
                "root": str(Path(DATASET_DIR).as_posix())
            }
        else:
            self.annotations["_meta"] = {
                "completed": False,
                "timestamp": datetime.now().isoformat(),
                "root": str(Path(DATASET_DIR).as_posix())
            }
            
        with open(self.annotations_file, 'w') as f:
            json.dump(self.annotations, f, indent=2)
    
    def get_pair_annotation(self, pair_id):
        return self.annotations.get(f"{pair_id}", {
            "pair_state": None,
            "boxes": []
        })
    


    def _relative_path(self, abs_path):
        return str(Path(abs_path).resolve().relative_to(DATASET_DIR))
    
    
    def save_pair_annotation(self, image1, image2, pair_state, boxes=None):
        pair_id = str(image1.controller.current_index)
        print("[DEBUG] Saving annotation for pair_id:", pair_id)


        boxes1 = image1.get_boxes()
        boxes2 = image2.get_boxes()
        print(f"[DEBUG] image1 boxes: {len(boxes1)} | image2 boxes: {len(boxes2)}")

        collected_boxes = boxes1 + boxes2
        boxes_to_save = [b for b in collected_boxes if not b.get("synced_highlight")]

        final_boxes = []
        for box in boxes_to_save:
            entry = {
                "x1": box["x1"],
                "y1": box["y1"],
                "x2": box["x2"],
                "y2": box["y2"],
                "annotation_type": box["annotation_type"],
                "pair_id": box.get("pair_id")
            }


            final_boxes.append(entry)

    

        self.annotations[f"{pair_id}"] = {
            "pair_state": pair_state,
            "im1_path": make_relative_path(image1.image_path),
            "im2_path": make_relative_path(image2.image_path),
            "image1_size": image1.image_size,
            "image2_size": image2.image_size,
            "boxes": final_boxes
        }

        session_path = Path(make_relative_path(image1.image_path)).parent
        session_id = str(session_path).replace(os.sep, "_")
        pair_id_unique = f"{session_id}_{image1.controller.current_index}"

        print(f"[HIGHSCORE] Sending annotation for pair {pair_id_unique}: {pair_state}")
        report_annotation(USERNAME, class_name=pair_state, pair_id=pair_id_unique)


        self.save_annotations()
        print(f"[SAVE] Pair {pair_id} saved with {len(final_boxes)} boxes.")

