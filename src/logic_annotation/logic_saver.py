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


class AnnotationSaver(CommonSaver):
    def __init__(self, session_info, local_dir="./logs"):
        file_path = Path(local_dir) / session_info.store / session_info.session / "annotations.json"
        super().__init__(file_path)

        # init meta if missing
        self.annotations["_meta"].setdefault("completed", False)
        self.annotations["_meta"].setdefault("usable", True)
        self.annotations["_meta"].setdefault("timestamp", datetime.utcnow().isoformat())
        self._flush()

    def save_pair(self, pair, state, context=None, total_pairs=None):
        # context = SessionInfo in this mode
        self.annotations["items"][str(pair.pair_id)] = {
            "state": state,
            "timestamp": datetime.now().isoformat(),
        }

        # optional metadata
        self.annotations["_meta"]["total_pairs"] = total_pairs
        if total_pairs:
            self.annotations["_meta"]["completed"] = (
                len(self.annotations["items"]) >= total_pairs
            )

        self._flush()

    def update_meta(self):
        self.annotations["_meta"]["timestamp"] = datetime.utcnow().isoformat()
        self._flush()

    def mark_session_unusable(self):
        self.annotations["_meta"]["usable"] = False
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
        self.annotations["_meta"].setdefault("timestamp", datetime.utcnow().isoformat())
        self._flush()

    def update_meta(self):
        self.annotations["_meta"]["timestamp"] = datetime.utcnow().isoformat()
        self._flush()


class InconsistentSaver(ReviewSaver):
    def save_pair(self, pair, state, context=None, total_pairs=None):
        self.annotations["items"][str(pair.pair_id)] = {
            "pair_state": state,
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
        self._flush()


class UnsureSaver(ReviewSaver):
    def save_pair(self, pair, state, context=None, total_pairs=None):
        self.annotations["items"][str(pair.pair_id)] = {
            "pair_state": state,
            "boxes": pair.image1.boxes + pair.image2.boxes,
            "im1_path": getattr(pair.image1, "url", None),
            "im2_path": getattr(pair.image2, "url", None),
            "im1_size": pair.image1.img_size,
            "im2_size": pair.image2.img_size,
            "annotated_by": getattr(pair, "annotated_by", None),
        }
        self._flush()

