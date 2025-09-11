# review_unsure.py — updated for review_api_batch.py
import os
import json
import getpass  # fallback only
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from urllib.parse import urljoin

import requests

from app import ImagePairViewer
from config import DATASET_DIR, USERNAME, LOCAL_LOG_DIR
from ui_styles import init_ttk_styles

from typing import Optional, Dict 
# Local logging base dir + default legacy log
LOCAL_LOG_DIR = Path(LOCAL_LOG_DIR)
LOCAL_LOG_DIR.mkdir(parents=True, exist_ok=True)
LEGACY_LOG_PATH = LOCAL_LOG_DIR / "unsure_reviews.json"

# Server API base; override via env if needed
API_BASE = os.environ.get("REVIEW_API_BASE", "http://ml01:8081")

# Reviewer name: prefer config.USER; safe fallbacks
try:
    REVIEW_USER = USERNAME or getpass.getuser() or "unknown"
except Exception:
    REVIEW_USER = getpass.getuser() or "unknown"


class UnsureApp(tk.Tk):
    def __init__(self):
        super().__init__()
        init_ttk_styles(self)

        self.current_batch_id: str | None = None
        self.current_log_path: Path = LEGACY_LOG_PATH
        self.model_name = None
        self._set_title()

        # --- Toolbar ---
        bar = tk.Frame(self)
        tk.Button(bar, text="Load UNSURE (server)", command=self.load_unsure).pack(side="left", padx=4, pady=4)
        tk.Button(bar, text="Load INCONSISTENT (server)", command=self.load_inconsistent).pack(side="left", padx=4, pady=4)
        tk.Button(bar, text="Load NEXT BATCH (server)", command=self.load_next_inconsistent_batch).pack(side="left", padx=4, pady=4)
        tk.Button(bar, text="Upload Batch Results (server)", command=self.upload_batch_results).pack(side="left", padx=4, pady=4)
        bar.pack(side="top", fill="x")

        # --- Viewer: start empty (flat mode) ---
        self.viewer = ImagePairViewer(
            self,
            base_src=None,
            flat_pairs=[],
            _unsure_log_path=self.current_log_path  # swapped per-batch
        )
        self.viewer.pack(fill="both", expand=True)

    # ---------------- HTTP helpers ----------------

    def _get(self, path: str, params: Optional[Dict] = None):
        try:
            r = requests.get(urljoin(API_BASE, path), params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            messagebox.showerror("Network error", f"GET {path} failed:\n{e}")
            return None

    def _post(self, path: str, json_payload: dict):
        try:
            r = requests.post(urljoin(API_BASE, path), json=json_payload, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            messagebox.showerror("Network error", f"POST {path} failed:\n{e}")
            return None

    # ---------------- UI helpers ----------------

    def _set_title(self):
        suffix = f" — user: {REVIEW_USER}"
        if self.current_batch_id:
            suffix += f" — batch: {self.current_batch_id}"
        if self.model_name:
            suffix += f" — model: {self.model_name}"
        self.title("Unsure Review Mode" + suffix)

    def _merge_remote(self, items):
        """
        Adapt server items to the viewer's flat format and merge uniquely.
        Viewer expects: store_session_path, pair_id, im1_url, im2_url, unsure_by (and optionally predicted/expected).
        """
        if not items:
            messagebox.showinfo("Loaded", "No items returned")
            return

        flat = []
        for it in items:
            try:
                flat.append({
                    "store_session_path": it["store_session_path"],
                    "pair_id": int(it["pair_id"]),
                    "im1_url": urljoin(API_BASE, it["im1_url"]),
                    "im2_url": urljoin(API_BASE, it["im2_url"]),
                    "unsure_by": it.get("unsure_by") or {},
                    "annotated_by": it.get("annotated_by") or {},
                    "predicted": it.get("predicted"),
                    "expected": it.get("expected"),
                    "boxes_expected": it.get("boxes_expected", []),
                    "boxes_predicted": it.get("boxes_predicted", []),
                    "source": "remote",
                    "model_name": it.get("model_name")
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

    # ---------------- button actions ----------------

    def load_unsure(self):
        data = self._get("/unsure")
        if data is not None:
            self._merge_remote(data)

    def load_inconsistent(self):
        data = self._get("/inconsistent")
        if data is not None:
            self._merge_remote(data)

    def load_next_inconsistent_batch(self, size: int = 100):
        """
        Reserve or reuse a unique batch for this reviewer.
        Server: GET /inconsistent/batch?user=<USER>&size=100
        Creates/returns review_batch_<id>.json server-side and we mirror a local file with the same id.
        """
        resp = self._get("/inconsistent/batch", params={"user": REVIEW_USER, "size": size})

        print("resp: ", resp)
        if not resp:
            return
        if "items" not in resp:
            messagebox.showerror("Batch error", f"Unexpected response:\n{resp}")
            return

        model_name = resp.get("model_name")
        self.viewer.model_name = model_name
        self.current_batch_id = resp.get("batch_id")
        if self.current_batch_id:
            self.current_log_path = LOCAL_LOG_DIR / f"review_batch_{self.current_batch_id}.json"
        else:
            # server might reply with {message: "...", items: [], count: 0}
            self.current_log_path = LOCAL_LOG_DIR / "review_batch_none.json"

        # ensure the viewer writes to this per-batch file
        try:
            self.viewer._unsure_log_path = self.current_log_path
        except Exception:
            # if the viewer only reads that at init, re-instantiate
            self.viewer.destroy()
            self.viewer = ImagePairViewer(
                self, base_src=None, flat_pairs=[], _unsure_log_path=self.current_log_path
            )
            self.viewer.pack(fill="both", expand=True)

        # merge items
        self._merge_remote(resp.get("items", []))
        self._set_title()

        cnt = resp.get("count", len(resp.get("items", [])))
        if self.current_batch_id:
            messagebox.showinfo(
                "Batch loaded",
                f"Batch {self.current_batch_id} for '{REVIEW_USER}' with {cnt} items.\n"
                f"Local save: {self.current_log_path}"
            )
        else:
            messagebox.showinfo("Batch", resp.get("message", "No items"))

    def upload_batch_results(self):
        """
        Read the per-batch local JSON our viewer wrote and POST to:
          POST /batches/{batch_id}/results
        Body: dict keyed by 'store_session_path|pair_id' -> corrected record
        """
        if not self.current_batch_id:
            messagebox.showwarning("No batch", "Load a batch first.")
            return
        if not self.current_log_path.exists():
            messagebox.showwarning("Nothing to upload", f"No local file at {self.current_log_path}")
            return

        try:
            local_results = json.loads(self.current_log_path.read_text())
        except Exception as e:
            messagebox.showerror("Read error", f"Cannot parse {self.current_log_path}:\n{e}")
            return

        # Normalize into { "store_session_path|pair_id": entry }
        normalized: dict[str, dict] = {}
        meta_root = (local_results.get("_meta") or {}).get("root") if isinstance(local_results, dict) else ""

        if isinstance(local_results, dict):
            for k, v in local_results.items():
                if k == "_meta":
                    continue
                try:
                    store = v.get("store_session_path") or meta_root or ""
                    key = f"{store}|{int(k)}"
                    normalized[key] = v
                except Exception:
                    # accept already-composite keys
                    if isinstance(v, dict) and "|" in k:
                        normalized[k] = v

        if not normalized:
            messagebox.showwarning("Nothing to upload", "No review items found in the local batch file.")
            return

        resp = self._post(f"/batches/{self.current_batch_id}/results", json_payload=normalized)
        if resp:
            messagebox.showinfo("Upload", f"Server: {resp}")


if __name__ == "__main__":
    UnsureApp().mainloop()
