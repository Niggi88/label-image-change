# review_unsure.py
import os
import json
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from urllib.parse import urljoin

import requests

from app import ImagePairViewer
from config import DATASET_DIR
from ui_styles import init_ttk_styles

# where we store review decisions locally (unchanged)
LOG_PATH = Path(DATASET_DIR) / "unsure_reviews.json"

# server API base; override via env if you want
API_BASE = os.environ.get("REVIEW_API_BASE", "http://ml01:8081")


class UnsureApp(tk.Tk):
    def __init__(self):
        super().__init__()
        init_ttk_styles(self)

        self.title("Unsure Review Mode")

        # --- Toolbar (no auto-load; user decides what to fetch) ---
        bar = tk.Frame(self)
        tk.Button(bar, text="Load UNSURE (server)", command=self.load_unsure).pack(side="left", padx=4, pady=4)
        tk.Button(bar, text="Load INCONSISTENT (server)", command=self.load_inconsistent).pack(side="left", padx=4, pady=4)
        bar.pack(side="top", fill="x")

        # --- Viewer: start in flat mode with EMPTY list ---
        # Passing [] keeps _flat_mode=True without showing local unsure pairs
        self.viewer = ImagePairViewer(
            self,
            base_src=None,
            flat_pairs=[],                # <-- empty, no local auto-load
            _unsure_log_path=LOG_PATH     # pass the log path so outlines update
        )
        self.viewer.pack(fill="both", expand=True)

    # ------- helpers -------

    def _fetch(self, path: str):
        try:
            r = requests.get(urljoin(API_BASE, path), timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            messagebox.showerror("Network error", f"GET {path} failed:\n{e}")
            return []

    def _merge_remote(self, items):
        """
        Adapt server items to the viewer's flat format and merge uniquely.
        Viewer expects: store_session_path, pair_id, im1_url, im2_url, unsure_by (and optionally predicted/expected).
        """
        flat = []
        for it in items:
            try:
                flat.append({
                    "store_session_path": it["store_session_path"],
                    "pair_id": int(it["pair_id"]),
                    "im1_url": urljoin(API_BASE, it["im1_url"]),
                    "im2_url": urljoin(API_BASE, it["im2_url"]),
                    "unsure_by": it.get("unsure_by") or {},
                    # optional extras used by banner/outline:
                    "predicted": it.get("predicted"),
                    "expected": it.get("expected"),
                    "boxes_expected": it.get("boxes_expected", []),
                    "boxes_predicted": it.get("boxes_predicted", []),
                    "source": "remote",
                })
            except Exception as e:
                print("[REMOTE] skip item:", e)

        # merge into viewer
        try:
            added = self.viewer.image_pairs.extend_unique(flat)
        except Exception:
            # fallback if extend_unique isn't available
            self.viewer.image_pairs._items = flat
            added = len(flat)

        if added:
            self.viewer._flat_view_index = 0
            self.viewer.load_pair(0)
        messagebox.showinfo("Loaded", f"Added {added} pairs from server")

    # ------- button actions -------

    def load_unsure(self):
        self._merge_remote(self._fetch("/unsure"))

    def load_inconsistent(self):
        self._merge_remote(self._fetch("/inconsistent"))


if __name__ == "__main__":
    UnsureApp().mainloop()
