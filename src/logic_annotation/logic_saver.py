import json
from pathlib import Path
import uuid
from src.config import USERNAME, DATASET_DIR, LOCAL_LOG_DIR
from datetime import datetime
from urllib.parse import urlparse
from src.utils import report_annotation, report_inconsistent_review
import os

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
        old_state = self.annotations.get(pid, {}).get("pair_state")

        print(f"[DEBUG] save_pair for {pid}: old_state={old_state}, new_state={state}")

        entry = {
            "pair_state": state,
            "boxes": pair.image1.boxes + pair.image2.boxes,
            "im1_path": str(Path(context["session_info"].store) / context["session_info"].session / pair.img1_name),
            "im2_path": str(Path(context["session_info"].store) / context["session_info"].session / pair.img2_name),
            "image1_size": pair.image1.img_size,
            "image2_size": pair.image2.img_size,
        }


        print("\n=== DEBUG SAVE_PAIR ===")
        print("PAIR:", pid)
        print(" IMG1 DISPLAYED:", pair.img1_name)
        print(" IMG2 DISPLAYED:", pair.img2_name)
        print(" IMG1 ACTUALLY SAVED:", str(Path(context["session_info"].store) / context["session_info"].session / pair.img1_name))
        print(" IMG2 ACTUALLY SAVED:", str(Path(context["session_info"].store) / context["session_info"].session / pair.img2_name))
        print("----------")

        self.annotations[pid] = entry
        self.update_meta(context["progress"]["total"])
        self._flush()

        # 🔑 Build unique pair id = session + index
        session_id = str(context["session_info"].session).replace(os.sep, "_")
        pair_id_unique = f"{session_id}_{pid}"

        if state != old_state:
            # Skip first-time default (None → no_annotation)
            if not (old_state is None and state == "no_annotation"):
                print(f"[DEBUG] Reporting annotation change: {old_state} → {state}")
                report_annotation(
                    class_name=state,
                    pair_id=pair_id_unique   # ✅ use unique ID
                )
            else:
                print(f"[DEBUG] Skipping initial default save for {pid}")




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
            "root": str(DATASET_DIR),
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
                "im1_path": str(Path(context["session_info"].store) / context["session_info"].session / pair.img1_name),
                "im2_path": str(Path(context["session_info"].store) / context["session_info"].session / pair.img2_name),
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
    def __init__(self, batch_info: dict, local_dir=LOCAL_LOG_DIR):
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
        self.annotations.setdefault("_meta", {})

        # prefer stored total_pairs from batch metadata
        total_pairs = self.annotations["_meta"].get("total_pairs", total_pairs)

        self.annotations["_meta"]["timestamp"] = datetime.now().isoformat()
        self.annotations["_meta"]["reviewed_by"] = USERNAME

        annotated = len(self.annotations.get("items", {}))
        self.annotations["_meta"]["completed"] = (annotated >= total_pairs)

        print(f"completed? {self.annotations['_meta']['completed']}")

        self._flush()


class InconsistentSaver(ReviewSaver):

    def __init__(self, batch_meta, root_dir):
        self.root = Path(root_dir)
        self.batch_id = batch_meta.get("batch_id", "unknown")
        self.logfile = self.root / f"inconsistent_{self.batch_id}.json"

        if self.logfile.exists():
            self.annotations = json.loads(self.logfile.read_text())
        else:
            self.annotations = {"_meta": {"completed": False, "timestamp": None}}

        # Guarantee items dict
        if "items" not in self.annotations:
            self.annotations["items"] = {}

    def _key(self, pair):
        return str(pair.pair_id)

    def save_pair(self, pair, state, ctx):
        print("inconsistent saver is saving")
        key = self._key(pair)

        self.annotations["items"][key] = {
            "pair_state": state,
            "im1_path": pair.source_item["im1_url"],
            "im2_path": pair.source_item["im2_url"],
            "image1_size": pair.image1.img_size,
            "image2_size": pair.image2.img_size,
            "boxes": pair.image1.boxes  # oder kombiniert, je nachdem
        }

        predicted = pair.source_item.get("predicted")
        expected = pair.source_item.get("expected")
        model_name = pair.source_item.get("model_name")

        decision = "accepted" if state=="accepted" else "corrected"

        report_inconsistent_review(
            pair_id=key,
            predicted=predicted,
            expected=expected,
            reviewer=ctx.get("user"),
            decision=decision,
            model_name=model_name
        )



        self._flush()


    def reset_pair(self, pair, context):

        pid = str(pair.pair_id)
        print("pid: ", pid)
        key = f"{pair.source_item['store_session_path']}|{pair.source_item['pair_id']}"
        print("source_item: ", key)
        if pid != key:
            print("False")
            return False
        print("True")
        key = self._key(pair)
        self.annotations["items"][key]["pair_state"] = pair.source_item.get("expected")
        print("state after reset: ", self.annotations["items"][key]["pair_state"])
        
        # self.annotations[pid]["boxes"] = []
        # clear in-memory boxes
        pair.image1.boxes.clear()
        pair.image2.boxes.clear()

        self._flush()
        
    # def save_correct(self, pair, expected_entry, ctx):
    #     """Reviewer bestätigt expected."""
    #     key = str(pair.pair_id)

    #     old = self.annotations["items"].get(key, {})
    #     pair_state = expected_entry.get("expected", "no_annotation")

    #     # Update local JSON
    #     self.annotations["items"][key] = {
    #         "pair_state": pair_state,
    #         "im1_path": expected_entry["im1_url"],
    #         "im2_path": expected_entry["im2_url"],
    #         "image1_size": pair.image1.img_size,
    #         "image2_size": pair.image2.img_size,
    #         "boxes": expected_entry.get("boxes_expected", []),
    #     }

    #     report_inconsistent_review(
    #         pair_id=key,
    #         predicted=pair.source_item.get("predicted", []),
    #         expected=expected_entry.get("expected", []),
    #         reviewer= USERNAME,
    #         decision="accepted",
    #         model_name=ctx.get("model_name", "unknown-model"),
    #     )


    #     pair.source_item["boxes_expected"] = expected_entry.get("boxes_expected", [])

    #     total = ctx["progress"]["total"]
    #     self.update_meta(total)

    #     self._flush()


    def _flush(self):
        self.annotations["_meta"]["timestamp"] = datetime.now().isoformat()
        self.logfile.write_text(json.dumps(self.annotations, indent=2))


class UnsureSaver(ReviewSaver):
    def save_pair(self, pair, state, context):
        key = f"{pair.source_item['store_session_path']}|{pair.pair_id}"
        self.annotations["items"][key] = {
            "pair_state": state,
            "timestamp": datetime.now().isoformat(),
            "boxes": pair.image1.boxes + pair.image2.boxes,
            "im1_path": _shorten_path(getattr(pair.image1, "url", str(pair.image1.img_path))),
            "im2_path": _shorten_path(getattr(pair.image2, "url", str(pair.image2.img_path))),
            "im1_size": pair.image1.img_size,
            "im2_size": pair.image2.img_size,
            "reviewed_by": context.get("user"),
        }
        self.update_meta(context["progress"]["total"])
        self._flush()

    def save_box(self, pair, box, context, state="annotated"):
        key = f"{pair.source_item['store_session_path']}|{pair.pair_id}"

        if key not in self.annotations["items"]:
            self.annotations["items"][key] = {
                "pair_state": state,
                "boxes": [],
                "reviewed_by": context.get("user"),
                "im1_path": _shorten_path(getattr(pair.image1, "url", str(pair.image1.img_path))),
                "im2_path": _shorten_path(getattr(pair.image2, "url", str(pair.image2.img_path))),
                "im1_size": pair.image1.img_size,
                "im2_size": pair.image2.img_size,
            }

        full_box = {
            "x1": box["x1"], "y1": box["y1"],
            "x2": box["x2"], "y2": box["y2"],
            "box_id": box.get("box_id", str(uuid.uuid4())),
            "annotation_type": box["annotation_type"],
        }

        # Save to JSON
        self.annotations["items"][key]["boxes"].append(full_box)
        self.annotations["items"][key]["pair_state"] = state

        # Keep in-memory boxes updated
        if box.get("image_id") == 1:
            pair.image1.boxes.append(full_box)
        elif box.get("image_id") == 2:
            pair.image2.boxes.append(full_box)

        self.update_meta(context["progress"]["total"])
        self._flush()