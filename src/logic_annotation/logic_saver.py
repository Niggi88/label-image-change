import json
from pathlib import Path
import uuid
import src.config
from datetime import datetime
from urllib.parse import urlparse


def _shorten_path(path_or_url: str) -> str:
    """
    Convert either a full URL or a filesystem path into store/session/img_name.
    """
    # Handle URLs
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        parts = Path(urlparse(path_or_url).path).parts
    else:
        parts = Path(path_or_url).parts

    if "images" in parts:
        idx = parts.index("images")
        return str(Path(*parts[idx+1:]))
    return str(Path(*parts))


from abc import ABC, abstractmethod
class BaseSaver(ABC):
    @abstractmethod
    def save_pair(self, pair, state, context):
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
    def save_box(self, pair, box, context, state="annotated"):
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

    def save_box(self, pair, box, context, state="annotated"):
        self.annotations["items"].setdefault(str(pair.pair_id), {}).setdefault("boxes", []).append(box)
        self._flush()

    def save_delete_box(self, pair, box_id, context):
        boxes = self.annotations["items"].get(str(pair.pair_id), {}).get("boxes", [])
        self.annotations["items"][str(pair.pair_id)]["boxes"] = [
            b for b in boxes if b.get("box_id") != box_id   # ✅ consistent
        ]
        self._flush()

    def reset_pair(self, pair, context):
        pid = str(pair.pair_id)
        if str(pair.pair_id) in self.annotations["items"]:
            self.annotations["items"][pid] = {
                "pair_state": "no_annotation",
                "boxes": [],
                "timestamp": datetime.now().isoformat(),
            }
            # clear boxes in memory
            pair.image1.boxes.clear()
            pair.image2.boxes.clear()
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

    def save_pair(self, pair, state, context):
        pid = str(pair.pair_id)
        entry = {
            "pair_state": state,
            "boxes": pair.image1.boxes + pair.image2.boxes,
            "im1_path": str(Path(context["session_info"].store) / context["session_info"].session / pair.image1.img_name),
            "im2_path": str(Path(context["session_info"].store) / context["session_info"].session / pair.image2.img_name),
            "image1_size": pair.image1.img_size,
            "image2_size": pair.image2.img_size,
        }
        self.annotations[pid] = entry
        self.update_meta(context["progress"]["total"])
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
        
    def save_box(self, pair, box, context, state="annotated"):
        """
        Save a single new box into annotations.json.
        Ensures pair entry exists, and appends the box with correct structure.
        """
        total_pairs = context["progress"]["total"]

        pid = str(pair.pair_id)

        # Ensure the pair exists
        if pid not in self.annotations:
            self.annotations[pid] = {
                "pair_state": state,
                "boxes": [],
                "im1_path": str(Path(context["session_info"].store) / context["session_info"].session / pair.image1.img_name),
                "im2_path": str(Path(context["session_info"].store) / context["session_info"].session / pair.image2.img_name),
                "image1_size": pair.image1.img_size,
                "image2_size": pair.image2.img_size,
            }

        # Ensure the box has required fields
        full_box = {
            "x1": box["x1"],
            "y1": box["y1"],
            "x2": box["x2"],
            "y2": box["y2"],
            "box_id": box.get("box_id", str(uuid.uuid4())),
            "annotation_type": box["annotation_type"],
        }

        self.annotations[pid]["boxes"].append(full_box)

        # Always update pair state
        self.annotations[pid]["pair_state"] = state
        self.update_meta(total_pairs)
        self._flush()

    def save_delete_box(self, pair, box_id, context):
        """
        Delete a box from annotations.json by its box_id.
        """
        total_pairs = context["progress"]["total"]

        pid = str(pair.pair_id)
        if pid not in self.annotations:
            return False  # nothing to delete

        before = len(self.annotations[pid]["boxes"])
        self.annotations[pid]["boxes"] = [
            b for b in self.annotations[pid]["boxes"]
            if b.get("box_id") != box_id   # ✅ use "box_id" not "pair_id"
        ]
        after = len(self.annotations[pid]["boxes"])

        if before != after:
            self.update_meta(total_pairs)
            self._flush()
            return True  # deleted something
        return False

    
    def reset_pair(self, pair, context):

        pid = str(pair.pair_id)
        if pid not in self.annotations:
            return False
        
        self.annotations[pid]["pair_state"] = "no_annotation"
        self.annotations[pid]["boxes"] = []
        # clear in-memory boxes
        pair.image1.boxes.clear()
        pair.image2.boxes.clear()

        self._flush()



class ReviewSaver(CommonSaver):
    def __init__(self, batch_info: dict, local_dir=src.config.LOCAL_LOG_DIR):
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

    def update_meta(self, total_pairs):
        """Update progress meta information."""
        self.annotations.setdefault("_meta", {})

        # Always update timestamp
        self.annotations["_meta"]["timestamp"] = datetime.now().isoformat()


        annotated = len(self.annotations.get("items", {}))
        self.annotations["_meta"]["completed"] = (
            annotated >= total_pairs and total_pairs > 0
        )

        self._flush()



class InconsistentSaver(ReviewSaver):
    def save_pair(self, pair, state, context):
        pid = str(pair.pair_id)

        self.annotations["items"][pid] = {
            "pair_state": state,
            "timestamp": datetime.now().isoformat(),
            "boxes": pair.image1.boxes + pair.image2.boxes,
            "im1_path": _shorten_path(getattr(pair.image1, "url", str(pair.image1.img_path))),
            "im2_path": _shorten_path(getattr(pair.image2, "url", str(pair.image2.img_path))),
            "im1_size": pair.image1.img_size,
            "im2_size": pair.image2.img_size,
            "expected": getattr(pair, "expected", None),
            "predicted": getattr(pair, "predicted", None),
            "annotated_by": getattr(pair, "annotated_by", None),
            "model_name": getattr(pair, "model_name", None),
            # keep store_session_path as metadata, not as a key
            "store_session_path": getattr(pair, "source_item", {}).get("store_session_path")
                if hasattr(pair, "source_item") else None,
        }

        self.update_meta(context["progress"]["total"])
        self._flush()

    def save_box(self, pair, box, context, state="annotated"):
        pid = str(pair.pair_id)

        if pid not in self.annotations["items"]:
            self.annotations["items"][pid] = {
                "pair_state": state,
                "boxes": [],
                "expected": getattr(pair, "expected", None),
                "predicted": getattr(pair, "predicted", None),
                "annotated_by": getattr(pair, "annotated_by", None),
                "model_name": getattr(pair, "model_name", None),
                "store_session_path": pair.source_item.get("store_session_path")
                    if hasattr(pair, "source_item") else None,
            }

        full_box = {
            "x1": box["x1"], "y1": box["y1"], "x2": box["x2"], "y2": box["y2"],
            "box_id": box.get("box_id", str(uuid.uuid4())),
            "annotation_type": box["annotation_type"],
        }

        # Save to JSON + ensure pair_state is 'annotated'
        self.annotations["items"][pid]["boxes"].append(full_box)
        self.annotations["items"][pid]["pair_state"] = state

        # Keep in-memory boxes in sync (helps immediate UI)
        if box.get("image_id") == 1:
            pair.image1.boxes.append(full_box)
        elif box.get("image_id") == 2:
            pair.image2.boxes.append(full_box)

        self.update_meta(context["progress"]["total"])
        self._flush()



class UnsureSaver(ReviewSaver):
    def save_pair(self, pair, state, context):
        self.annotations["items"][str(pair.pair_id)] = {
            "pair_state": state,   # ✅ align with InconsistentSaver
            "timestamp": datetime.now().isoformat(),
            "boxes": pair.image1.boxes + pair.image2.boxes,
            "im1_path": _shorten_path(getattr(pair.image1, "url", str(pair.image1.img_path))),
            "im2_path": _shorten_path(getattr(pair.image2, "url", str(pair.image2.img_path))),
            "im1_size": pair.image1.img_size,
            "im2_size": pair.image2.img_size,
            "annotated_by": getattr(pair, "annotated_by", None),
        }
        self.update_meta(context["progress"]["total"])
        self._flush()
