import json
from pathlib import Path
import tkinter as tk
from app import ImagePairViewer
from config import DATASET_DIR

def collect_unsure_pairs(dataset_dir):
    items = []
    base = Path(dataset_dir)
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
                # "unsure" ≙ no_annotation  (+ optional: fehlender Zustand)
                ps = entry.get("pair_state")
                if ps in (None, "no_annotation"):
                    # Im1/Im2-Pfade (wir nehmen die Dateinamen aus dem JSON oder
                    # bauen sie aus dem Session-Ordner; falls du die Felder anders benennst, hier anpassen)
                    im1 = session_dir / Path(entry["im1_path"]).name
                    im2 = session_dir / Path(entry["im2_path"]).name
                    items.append({
                        "session_path": session_dir,
                        "pair_id": int(k),
                        "im1_path": im1,
                        "im2_path": im2,
                    })
    print("unsure pairs length:", len(items))
    return items

class UnsureApp(tk.Tk):
    def __init__(self, flat_items):
        super().__init__()
        self.title("Unsure Review Mode")
        self.viewer = ImagePairViewer(self, base_src=None, flat_pairs=flat_items, unsure_log_path=Path(DATASET_DIR) / "unsure_reviews.json")
        self.viewer.pack(fill="both", expand=True)

if __name__ == "__main__":
    unsure = collect_unsure_pairs(DATASET_DIR)
    if not unsure:
        print("No unsure annotations found.")
    else:
        app = UnsureApp(unsure)
        app.mainloop()
