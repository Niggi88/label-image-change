import json
from pathlib import Path
import uuid
import src.config
from datetime import datetime

from abc import ABC, abstractmethod
class BaseSaver(ABC):
    @abstractmethod
    def save_pair(self, pair, state, context=None, total_pairs=None):
        pass

    @abstractmethod
    def set_on_change(self):
        pass

    @abstractmethod
    def _flush(self):
        pass

    @abstractmethod
    def update_meta(self):
        pass

    @abstractmethod
    def save_box(self):
        pass

    @abstractmethod
    def save_delete_box(self):
        pass

    @abstractmethod
    def reset_pair(self):
        pass


class CommonSaver(BaseSaver):
    def __init__(self, file_path: Path):
        self.file = Path(file_path)
        self.file.parent.mkdir(parents=True, exist_ok=True)


        self._on_change = None

        # Load or create annotations JSON
        if self.file.exists():
            with open(self.file, "r") as f:
                self.annotations = json.load(f)
        else:
            self.annotations = {"_meta": {}, "items": {}}
            self._flush()


    # ------------- Common stuff (yellow in your diagram) -----------

    def set_on_change(self, cb):
        self._on_change = cb

    def _flush(self):
        with open(self.file, "w") as f:
            json.dump(self.annotations, f, indent=2)

        if self._on_change:
            self._on_change()

    def save_box(self, pair_id, box):
        self.annotations["items"].setdefault(str(pair_id), {}).setdefault("boxes", []).append(box)
        self._flush()

    def save_delete_box(self, pair_id, box_id):
        boxes = self.annotations["items"].get(str(pair_id), {}).get("boxes", [])
        self.annotations["items"][str(pair_id)]["boxes"] = [b for b in boxes if b.get("id") != box_id]
        self._flush()

    def reset_pair(self, pair_id):
        if str(pair_id) in self.annotations["items"]:
            self.annotations["items"].pop(str(pair_id))
            self._flush()

    # meta must be customized in children
    def update_meta(self):
        raise NotImplementedError


class AnnotationSaver:
    def __init__(self, info):
        
        self.saving_path = Path(info.path)
        self.file = self.saving_path / "annotations.json"

        if self.file.exists():
            self.annotations = json.loads(self.file.read_text())
        else:
            self.annotations = {}


        self._on_change = None  # callback

    def save_pair(self, pair, state, info, total_pairs):
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
        pid_count = sum(1 for k in self.annotations if k != "_meta")
        completed = pid_count >= total_pairs

        if "_meta" not in self.annotations:
            self.annotations["_meta"] = {}

        self.annotations["_meta"].update({
            "completed": completed,
            "timestamp": datetime.now().isoformat(),
            "root": str(src.config.DATASET_DIR),
            "usable": self.annotations["_meta"].get("usable", True)  # default True
        })

    def mark_session_unusable(self):
        """Mark this session as unusable in annotations.json and save."""
        if "_meta" not in self.annotations:
            self.annotations["_meta"] = {}

        self.annotations["_meta"]["usable"] = False
        self._flush()
        
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



class ReviewSaver(CommonSaver):
    def __init__(self, batch_info: dict, local_dir="./review_logs"):
        batch_id = batch_info["batch_id"]
        batch_type = batch_info["batch_type"]

        file_path = Path(local_dir) / f"{batch_type}_batch_{batch_id}.json"
        super().__init__(file_path)

        # init meta if missing
        self.annotations["_meta"].setdefault("batch_id", batch_id)
        self.annotations["_meta"].setdefault("batch_type", batch_type)
        self.annotations["_meta"].setdefault("reviewer", batch_info.get("reviewer"))
        self.annotations["_meta"].setdefault("completed", False)
        self.annotations["_meta"].setdefault("timestamp", datetime.now().isoformat())
        self.annotations["_meta"].setdefault("total_pairs", batch_info.get("count"))
        self._flush()

    def update_meta(self):
        self.annotations["_meta"]["timestamp"] = datetime.now().isoformat()
        self._flush()


class InconsistentSaver(ReviewSaver):
    def save_pair(self, pair, state, context=None, total_pairs=None):
        self.annotations["items"][str(pair.pair_id)] = {
            "state": state,
            "timestamp": datetime.now().isoformat(),
            "boxes": pair.image1.boxes + pair.image2.boxes,
            "im1_path": getattr(pair.image1, "url", None),
            "im2_path": getattr(pair.image2, "url", None),
            "im1_size": pair.image1.img_size,
            "im2_size": pair.image2.img_size,
            "expected": getattr(pair, "expected", None),
            "predicted": getattr(pair, "predicted", None),
            "annotated_by": getattr(pair, "annotated_by", None),
            "model_name": getattr(pair, "model_name", None),
        }

        # update meta like in AnnotationSaver
        if total_pairs:
            self.annotations["_meta"]["total_pairs"] = total_pairs
            self.annotations["_meta"]["completed"] = (
                len(self.annotations["items"]) >= total_pairs
            )

        self._flush()

    def save_box(self, pair, box, total_pairs, state="annotated"):
        key = f"{pair.source_item['store_session_path']}|{pair.pair_id}"

        if key not in self.annotations:
            self.annotations[key] = {
                "pair_state": state,
                "boxes": [],
                "expected": pair.expected,
                "predicted": pair.predicted,
                "annotated_by": pair.annotated_by,
                "model_name": pair.model_name,
            }

        full_box = {
            "x1": box["x1"],
            "y1": box["y1"],
            "x2": box["x2"],
            "y2": box["y2"],
            "pair_id": box.get("pair_id", str(uuid.uuid4())),
            "annotation_type": box["annotation_type"],
        }

        self.annotations[key]["boxes"].append(full_box)
        self.annotations[key]["pair_state"] = state
        self.update_meta(total_pairs)
        self._flush()


class UnsureSaver(ReviewSaver):
    def save_pair(self, pair, state, context=None, total_pairs=None):
        self.annotations["items"][str(pair.pair_id)] = {
            "state": state,
            "timestamp": datetime.now().isoformat(),
            "boxes": pair.image1.boxes + pair.image2.boxes,
            "im1_path": getattr(pair.image1, "url", None),
            "im2_path": getattr(pair.image2, "url", None),
            "im1_size": pair.image1.img_size,
            "im2_size": pair.image2.img_size,
            "annotated_by": getattr(pair, "annotated_by", None),
        }

        if total_pairs:
            self.annotations["_meta"]["total_pairs"] = total_pairs
            self.annotations["_meta"]["completed"] = (
                len(self.annotations["items"]) >= total_pairs
            )

        self._flush()

