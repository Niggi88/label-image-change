import json
from pathlib import Path
import uuid
import config
from datetime import datetime


class AnnotationSaver:
    def __init__(self, info):
        
        self.saving_path = Path(info.path)
        self.file = self.saving_path / "annotations.json"

        if self.file.exists():
            self.annotations = json.loads(self.file.read_text())
        else:
            self.annotations = {}


        self._on_change = None  # callback

    def save_pair(self, pair, info, state, total_pairs):
        """Speichere ein komplettes ImagePair mit state"""
        self.saving_path = info.path
        # pair = data_handler.current_pair()
        # info = data_handler.current_session_info()

        entry = {
            "pair_state": state,
            "boxes": pair.image1.boxes + pair.image2.boxes,
            "im1_path": str(Path(info.store) / info.session / pair.image1.img_name),
            "im2_path": str(Path(info.store) / info.session / pair.image2.img_name),
            "image1_size": pair.image1.img_size,
            "image2_size": pair.image2.img_size,
        }
        self.annotations[str(pair.pair_id)] = entry
        pair.pair_annotation = state
        self.update_meta(total_pairs)
        self._flush()


    def set_on_change(self, callback):
        """UI can register refresh here."""
        self._on_change = callback

    def _flush(self):
        self.file.write_text(json.dumps(self.annotations, indent=2))
        if self._on_change:
            self._on_change()

    def update_meta(self, total_pairs):
        # Check if all pairs are annotated (have a pair_state)
        pid_count = sum(1 for k in self.annotations if k != "_meta")
        completed = pid_count >= total_pairs

        self.annotations["_meta"] = {
            "completed": completed,
            "timestamp": datetime.now().isoformat(),
            "root": str(config.DATASET_DIR),
            "usable": self.annotations["_meta"].get("usable", True)  # default True
        }

    def save_box(self, pair, info, box, total_pairs, state="annotated"):
        """
        Save a single new box into annotations.json.
        Ensures pair entry exists, and appends the box with correct structure.
        """


        pid = str(pair.pair_id)

        # Ensure the pair exists
        if pid not in self.annotations:
            self.annotations[pid] = {
                "pair_state": state,
                "boxes": [],
                "im1_path": str(Path(info.store) / info.session / pair.image1.img_name),
                "im2_path": str(Path(info.store) / info.session / pair.image2.img_name),
                "image1_size": pair.image1.img_size,
                "image2_size": pair.image2.img_size,
            }

        # Ensure the box has required fields
        full_box = {
            "x1": box["x1"],
            "y1": box["y1"],
            "x2": box["x2"],
            "y2": box["y2"],
            "pair_id": box.get("pair_id", str(uuid.uuid4())),
            "annotation_type": box["annotation_type"],
        }

        self.annotations[pid]["boxes"].append(full_box)

        # Always update pair state
        self.annotations[pid]["pair_state"] = state
        self.update_meta(total_pairs)
        self._flush()

    def save_delete_box(self, pair, box_id, total_pairs, info):
        """
        Delete a box from annotations.json by its pair_id.
        """
        pid = str(pair.pair_id)
        if pid not in self.annotations:
            return False  # nothing to delete

        before = len(self.annotations[pid]["boxes"])
        self.annotations[pid]["boxes"] = [
            b for b in self.annotations[pid]["boxes"]
            if b["pair_id"] != box_id
        ]
        after = len(self.annotations[pid]["boxes"])

        if before != after:
            self.update_meta(total_pairs)
            self._flush()
            return True  # deleted something
        return False
    
    def reset_pair(self, pair):

        pid = str(pair.pair_id)
        if pid not in self.annotations:
            return False
        
        self.annotations[pid]["pair_state"] = "no_annotation"
        self.annotations[pid]["boxes"] = []

        self._flush()