import json
from pathlib import Path
import uuid

class AnnotationSaver:
    def __init__(self, saving_path):
        self.saving_path = Path(saving_path)
        self.file = self.saving_path / "annotations.json"

        if self.file.exists():
            self.annotations = json.loads(self.file.read_text())
        else:
            self.annotations = {}

    def save_pair(self, pair, state):
        """Speichere ein komplettes ImagePair mit state"""
        entry = {
            "pair_state": state,
            "boxes": pair.image1.boxes + pair.image2.boxes,
            "im1_path": str(pair.image1.img_path),
            "im2_path": str(pair.image2.img_path),
            "image1_size": pair.image1.img_size,
            "image2_size": pair.image2.img_size,
        }
        self.annotations[str(pair.pair_id)] = entry
        self._flush()

    def _flush(self):
        self.file.write_text(json.dumps(self.annotations, indent=2))

    def save_box(self, pair, box, state="annotated"):
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
                "im1_path": str(pair.image1.img_path),
                "im2_path": str(pair.image2.img_path),
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

        self._flush()

