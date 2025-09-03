# review_unsure.py
import json
from pathlib import Path
import tkinter as tk
from app import ImagePairViewer
from config import DATASET_DIR

LOG_PATH = Path(DATASET_DIR) / "unsure_reviews.json"

def _load_unsure_log():
    try:
        if LOG_PATH.exists():
            return json.loads(LOG_PATH.read_text())
    except Exception as e:
        print("[WARN] failed reading unsure log:", e)
    return {}

def _already_corrected(log, session_path: Path, pair_id: int) -> bool:
    """
    Return True if this pair has a non-`no_annotation` state in unsure_reviews.json.
    Key format must match how we write it: f"{session_path}|{pair_id}"
    """
    key = f"{str(session_path)}|{int(pair_id)}"
    entry = log.get(key)
    if not entry:
        return False
    state = entry.get("pair_state")
    return state is not None and state != "no_annotation"

def collect_unsure_pairs(dataset_dir):
    items = []
    base = Path(dataset_dir)
    unsure_log = _load_unsure_log()

    for store_dir in sorted(base.glob("store_*")):
        for session_dir in sorted(store_dir.glob("session_*")):
            ann = session_dir / "annotations.json"
            if not ann.exists():
                continue

            try:
                data = json.loads(ann.read_text())
            except json.JSONDecodeError:
                continue

            for k, entry in data.items():
                if k == "_meta":
                    continue

                # Consider pairs that are unsure in the session (None or no_annotation)
                ps = entry.get("pair_state")
                if ps not in (None, "no_annotation"):
                    continue

                # Skip pairs that have been reviewed/corrected already in unsure_reviews.json
                if _already_corrected(unsure_log, session_dir, int(k)):
                    continue

                # Resolve paths (adapt field names if yours differ)
                im1 = session_dir / Path(entry["im1_path"]).name
                im2 = session_dir / Path(entry["im2_path"]).name

                items.append({
                    "store_session_path": str(session_dir),
                    "pair_id": int(k),
                    "im1_path": str(im1),
                    "im2_path": str(im2),
                    "im1_name": str(im1.name),
                    "im2_name": str(im2.name),
                })

    print("unsure pairs length:", len(items))
    return items

class UnsureApp(tk.Tk):
    def __init__(self, flat_items):
        super().__init__()
        self.title("Unsure Review Mode")
        # Pass the global log path so the viewer can read/write it
        self.viewer = ImagePairViewer(
            self,
            base_src=None,
            flat_pairs=flat_items,
            _unsure_log_path=LOG_PATH
        )
        self.viewer.pack(fill="both", expand=True)

if __name__ == "__main__":
    unsure = collect_unsure_pairs(DATASET_DIR)
    if not unsure:
        print("No unsure annotations found (after applying unsure_reviews.json filter).")
    else:
        app = UnsureApp(unsure)
        app.mainloop()
