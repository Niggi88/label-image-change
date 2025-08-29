import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from pathlib import Path
from utils import resize_with_aspect_ratio, flush_annotation_cache
from horizontal_spinner import HorizontalSpinner
# from image_cache import ImageCache
from image_annotation import ImageAnnotation
from annotatable_image import AnnotatableImage
import tkinter.messagebox as messagebox
from config import *
from pathlib import Path
import base64
import io
import copy
import json
import requests
import threading  # ensure this import exists at top of file
import time
import os
from urllib.parse import urlparse

# Remote API (override via env variables if you want)
API_BASE_URL = "http://172.30.20.31:8081"
# API_BASE_URL = os.getenv("UNSURE_API_BASE", "http://127.0.0.1:8081")
API_TOKEN    = os.getenv("UNSURE_API_TOKEN", "")
API_TIMEOUT  = int(os.getenv("UNSURE_API_TIMEOUT", "20"))


class ImagePairList(list):
    def __init__(self, src):

        self.src = Path(src)

        self.images = sorted(self.src.glob("*.jpeg"), key=lambda file: int(file.name.split("-")[0]))
        assert len(self.images) > 0, f"no images found at {src}"
        self.image_pairs = list(zip(self.images[:-1], self.images[1:]))

    def __getitem__(self, index):
        # Allow indexing into image_pairs
        return self.image_pairs[index]
    
    def __iter__(self):
        return iter(self.image_pairs)
    
    def __len__(self):
        return len(self.image_pairs)
    
    def ids(self):
        return list(range(len(self)))


class FlatPairList:
    """
    Adapter für eine flache Liste aus unsicheren Paaren.
    Erwartet Items als Dict mit:
      - session_path: Path   (Session-Ordner mit annotations.json)
      - pair_id: int         (Original-Index in dieser Session)
      - im1_path: Path
      - im2_path: Path
    """
    def __init__(self, items):
        self._items = items

    def __getitem__(self, index):
        it = self._items[index]
        return (it["im1_path"], it["im2_path"])

    def __len__(self):
        return len(self._items)

    def ids(self):
        return list(range(len(self._items)))

    def meta_at(self, index):
        return self._items[index]

    def _key_of(self, it):
        return f"{str(it['session_path'])}|{int(it['pair_id'])}"

    def keys(self):
        return { self._key_of(it) for it in self._items }

    def extend_unique(self, items):
        """Append only new items, skip existing keys. Return number added."""
        existing = self.keys()
        added = 0
        for it in items:
            k = self._key_of(it)
            if k in existing:
                continue
            self._items.append(it)
            existing.add(k)
            added += 1
        return added


class PairViewerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        from tkinter import font

        self.tk.call('tk', 'scaling', UI_SCALING)

        self.title("Side by Side Images")
        
        default_font = font.nametofont("TkDefaultFont")

        default_font.configure(size=int(default_font['size'] * FONT_SCALING))

        # Define a consistent layout for all button styles
        style = ttk.Style()
        style.theme_use("default")

        # Klassifikationsfarben für Grundzustand
        button_colors = {
            "Nothing": "#ADD8E6",       # hellblau
            "Chaos": "#FFD700",         # gelb
            "NoAnnotation": "#B497B8"   # grau
        }

        for name, color in button_colors.items():
            style.configure(f"{name}.TButton",
                            background=color,
                            relief="flat",
                            borderwidth=1,
                            padding=(8, 6),
                            anchor="center")

            style.map(f"{name}.TButton",
                    background=[("active", "#CCCCCC"), ("pressed", "#CCCCCC")],
                    relief=[("pressed", "sunken"), ("!pressed", "flat")])

        # ✅ Annotate = grün
        style.configure("Annotate.TButton",
                        background="#66CC66",  # soft green
                        relief="flat",
                        borderwidth=1,
                        padding=(8, 6),
                        anchor="center")

        style.map("Annotate.TButton",
                background=[("active", "#CCCCCC"), ("pressed", "#CCCCCC")],
                relief=[("pressed", "sunken"), ("!pressed", "flat")])


        # 🗑️ Delete Selected Box = helleres rot
        style.configure("Delete.TButton",
                        background="#FF9999",  # ✅ korrektes Format
                        relief="flat",
                        borderwidth=1,
                        padding=(8, 6),
                        anchor="center")

        style.map("Delete.TButton",
                    background=[("active", "#CCCCCC"), ("pressed", "#CCCCCC")],
                    relief=[("pressed", "sunken"), ("!pressed", "flat")])

        # ❌ Clear All = rot
        style.configure("Clear.TButton",
                        background="#FF6666",  # soft red
                        relief="flat",
                        borderwidth=1,
                        padding=(8, 6),
                        anchor="center")

        style.map("Clear.TButton",
                background=[("active", "#CCCCCC"), ("pressed", "#CCCCCC")],
                relief=[("pressed", "sunken"), ("!pressed", "flat")])


        style.configure("Unsure.TButton",
                                background="#B497B8",
                                relief="flat",
                                borderwidth=1,
                                padding=(8, 6),
                                anchor="center")
        style.map("Unsure.TButton",
                background=[("active", "#CCCCCC"), ("pressed", "#CCCCCC")],
                relief=[("pressed", "sunken"), ("!pressed", "flat")])

            # Create the pair viewer with required arguments
        self.pair_viewer = ImagePairViewer(self, DATASET_DIR)
            
        self.pair_viewer.pack(fill="both", expand=True)



class ImagePairViewer(ttk.Frame):
    def __init__(self, container, base_src, flat_pairs=None, unsure_log_path=None):
        super().__init__(container)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        self._flat_mode = flat_pairs is not None
        self._flat_view_index = 0  # Position in der flachen Liste

        self._current_outline_color = None

        # Flicker state (works in both modes)
        self.flicker_running = False
        self.flicker_active = False

        self._unsure_log_path = unsure_log_path  # None in session mode

        def _build_scaffold():
            # (du hast das bereits in __init__ inline – wir nutzen weiter DEINE Widgets,
            # nur das Packen/Verstecken vom Skip-Button ändern wir im nächsten Schritt)
            pass


                # --- Wenn Flat-Modus: keine Sessions scannen, UI wie gewohnt bauen ---
        if self._flat_mode:

            # Bilder/Topbar/Controls wie in deinem bestehenden Code bauen:
            self.image1 = AnnotatableImage(self, annotation_controller=None, controller=self)
            self.image1.grid(row=1, column=0, sticky="nsew")
            self.image2 = AnnotatableImage(self, annotation_controller=None, controller=self)
            self.image2.grid(row=1, column=1, sticky="nsew")

            self.setup_controls()

            self.spinbox = HorizontalSpinner(self, [], self.set_images)
            self.spinbox.grid(row=3, column=0, columnspan=2)

            # ─ Top Bar (wie bei dir) ─
            top_bar = ttk.Frame(self)
            top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(8, 4))
            top_bar.columnconfigure(0, weight=1)

            self.global_progress_label = ttk.Label(top_bar, anchor="w")
            self.global_progress_label.grid(row=0, column=0, sticky="w")

            self.top_right_container = ttk.Frame(top_bar)
            self.top_right_container.grid(row=0, column=1, sticky="e")

            self.flicker_label = ttk.Label(self.top_right_container, text="Flickering", foreground="green")

            # Skip-Button im Flat-Modus NICHT anzeigen
            self.skip_session_btn = ttk.Button(
                self.top_right_container, text="Skip This Session",
                style="Danger.TButton", command=self.skip_current_session
            )
            # self.skip_session_btn.pack()  # <-- im Flat-Modus NICHT packen

            self.flush_btn = ttk.Button(self.top_right_container, text="Flush Cache",
                                        style="Clear.TButton", command=self.flush_cache)
            self.flush_btn.pack(pady=(4, 0))

            self.load_remote_btn = ttk.Button(
                self.top_right_container,
                text="Load Remote",
                style="Nothing.TButton",  # reuse any of your styles
                command=self._on_load_remote_clicked
            )
            self.load_remote_btn.pack(pady=(4, 0))


            # Datenquelle setzen
            self.image_pairs = FlatPairList(flat_pairs)
            self.annotations = None            # wird pro Pair auf die passende Session umgeschaltet
            self.current_index = 0             # bleibt der "original pair_id" Wert der Session
            self.in_annotation_mode = False

            # Spinner füttern
            self.spinbox.items = self.image_pairs.ids()
            self.spinbox.current_index = 0
            self.spinbox.draw_items()

            # Tastenbelegung & erstes Bild laden
            self.setup_key_bindings()
            self.load_pair(0)
            return  # wichtig: Session-Init überspringen
        

        self.session_paths = self.find_session_paths(base_src)
        assert self.session_paths, "No sessions found!"

        # Ask user if they want to skip fully annotated sessions
        skip_completed = messagebox.askyesno(
            "Skip Complete Sessions",
            "Do you want to skip sessions marked as fully annotated?"
        )

        if skip_completed:
            filtered_paths = []
            for session_path in self.session_paths:
                annotation_file = session_path / "annotations.json"
                if annotation_file.exists():
                    try:
                        with open(annotation_file, "r") as f:
                            data = json.load(f)
                        if not data.get("_meta", {}).get("completed", False):
                            filtered_paths.append(session_path)
                    except Exception as e:
                        print(f"Failed to read {annotation_file}: {e}")
                        filtered_paths.append(session_path)  # fail safe
                else:
                    filtered_paths.append(session_path)  # no annotation yet
            self.session_paths = filtered_paths

        self.session_index = 0

        # INITIALISIERUNG — EINMALIG
        self.image1 = AnnotatableImage(self, annotation_controller=None, controller=self)
        self.image1.grid(row=1, column=0, sticky="nsew")
        self.image2 = AnnotatableImage(self, annotation_controller=None, controller=self)
        self.image2.grid(row=1, column=1, sticky="nsew")

        self.setup_controls()

        self.spinbox = HorizontalSpinner(self, [], self.set_images)
        self.spinbox.grid(row=3, column=0, columnspan=2)

        # self.global_progress_label = ttk.Label(self, anchor="center")
        # self.global_progress_label.grid(row=0, column=0, columnspan=2, pady=(8, 4))

        # ─── TOP BAR ────────────────────────────────────────────────────────────────
        top_bar = ttk.Frame(self)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(8, 4))
        top_bar.columnconfigure(0, weight=1)

        self.global_progress_label = ttk.Label(top_bar, anchor="w")
        self.global_progress_label.grid(row=0, column=0, sticky="w")

        # Container for either the flicker label or the button
        self.top_right_container = ttk.Frame(top_bar)
        self.top_right_container.grid(row=0, column=1, sticky="e")

        self.flicker_label = ttk.Label(
            self.top_right_container,
            text="Flickering",
            foreground="green"
        )

        self.skip_session_btn = ttk.Button(
            self.top_right_container,
            text="Skip This Session",
            style="Danger.TButton",
            command=self.skip_current_session
        )

        # Start with the button shown
        self.skip_session_btn.pack()

        self.flush_btn = ttk.Button(
            self.top_right_container,
            text="Flush Cache",
            style="Clear.TButton",
            command=self.flush_cache
        )
        self.flush_btn.pack(pady=(4, 0))  # slight spacing below the skip button

        self.selected_box_index = None
        self.flicker_running = False
        self.flicker_active = False
        self._flicker_thread = None
        self._flicker_stop = threading.Event()

        self.reset(self.session_paths[self.session_index], initial=True)

    def _maybe_save(self, pair_state=None):
        """Session-Mode: normal speichern.
        Unsure-Mode (flat): nur global loggen, keine Session-Datei schreiben."""
        if getattr(self, "_flat_mode", False):
            # NUR globale Sammeldatei aktualisieren
            self._log_unsure_review(pair_state=pair_state)
            print("Save review_unsure.json: ", pair_state)
            return

        # Normaler Session-Mode: wie gehabt in annotations.json speichern
        self.annotations.save_pair_annotation(
            image1=self.image1,
            image2=self.image2,
            pair_state=pair_state
        )
        print("Save pair annotation.json: ", pair_state)



    def _log_unsure_review(self, pair_state=None):
        """Append/update a single record in unsure_reviews.json when in flat mode."""
        if not getattr(self, "_flat_mode", False):
            return
        if not self._unsure_log_path:
            return

        # Collect metadata
        meta = self.image_pairs.meta_at(self._flat_view_index)
        session_path = str(meta["session_path"])
        pair_id = int(meta["pair_id"])
        im1_path, im2_path = map(str, self._pair_imgs_at_current())

        # Get the current annotation payload
        ann = self.annotations.get_pair_annotation(self.current_index) or {}
        if pair_state is not None:
            ann = {**ann, "pair_state": pair_state}

        record = {
            "session_path": session_path,
            "pair_id": pair_id,
            "im1_path": im1_path,
            "im2_path": im2_path,
            "pair_state": ann.get("pair_state"),
            "boxes": ann.get("boxes", []),
            # optional extras:
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        }

        # Load -> upsert -> save (atomic-ish)
        try:
            existing = {}
            if self._unsure_log_path.exists():
                existing = json.loads(self._unsure_log_path.read_text())
        except Exception:
            existing = {}

        key = f"{session_path}|{pair_id}"
        existing[key] = record

        tmp = self._unsure_log_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(existing, indent=2))
        tmp.replace(self._unsure_log_path)

    def _shorten(self, s: str, maxlen: int = 40) -> str:
        """shorten very long filenames in the middle"""
        if len(s) <= maxlen:
            return s
        head = maxlen // 2 - 1
        tail = maxlen - head - 1
        return s[:head] + "…" + s[-tail:]

    def _unsure_key(self, session_path, pair_id: int) -> str:
        # Einheitlicher Key wie beim Schreiben
        return f"{str(session_path)}|{int(pair_id)}"

    def _get_unsure_entry(self, session_path, pair_id):
        """Liest (falls vorhanden) den Eintrag aus unsure_reviews.json"""
        if not getattr(self, "_unsure_log_path", None):
            return None
        try:
            if self._unsure_log_path.exists():
                data = json.loads(self._unsure_log_path.read_text())
                return data.get(self._unsure_key(session_path, pair_id))
        except Exception as e:
            print("[WARN] failed reading unsure log:", e)
        return None


    def redraw_outline(self):
        color = getattr(self, "_current_outline_color", None)
        # clear first (idempotent)
        self.image1.canvas.delete("canvas_outline")
        self.image2.canvas.delete("canvas_outline")
        if color:
            # draw again (use after_idle so it runs after image/masks/boxes are drawn)
            self.after_idle(lambda: self.image1.draw_canvas_outline(color))
            self.after_idle(lambda: self.image2.draw_canvas_outline(color))

    def _remote_headers(self):
        h = {}
        if API_TOKEN:
            h["Authorization"] = f"Bearer {API_TOKEN}"
        return h

    def _cache_dir(self):
        from config import DATASET_DIR
        # one cache per server host to avoid mixing if you change servers someday
        parsed = urlparse(API_BASE_URL)
        host_tag = (parsed.hostname or "remote") + (f"_{parsed.port}" if parsed.port else "")
        p = Path(DATASET_DIR) / ".remote_cache" / host_tag
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _cache_get(self, file_url: str) -> Path:
        """
        Download URL to local cache if not present.
        Preserve the original relative path after /images/.
        Examples:
        http://server:8081/images/store_x/session_y/000041.jpeg
            -> .remote_cache/server_8081/store_x/session_y/000041.jpeg
        """
        # prefix API_BASE_URL if server returned a relative URL like "/images/..."
        if not (file_url.startswith("http://") or file_url.startswith("https://")):
            file_url = f"{API_BASE_URL.rstrip('/')}{file_url}"

        parsed = urlparse(file_url)
        rel = parsed.path  # e.g. "/images/store_x/session_y/000041.jpeg"
        # strip the "/images/" prefix and keep the rest as the cache-relative path
        prefix = "/images/"
        if rel.startswith(prefix):
            rel = rel[len(prefix):]  # -> "store_x/session_y/000041.jpeg"
        else:
            # fallback: just use the basename if the path doesn't match expectation
            rel = rel.split("/")[-1]

        # build destination under cache dir, preserving subfolders
        dst = self._cache_dir() / Path(rel)
        dst.parent.mkdir(parents=True, exist_ok=True)

        if not dst.exists():
            rr = requests.get(file_url, headers=self._remote_headers(), timeout=API_TIMEOUT)
            rr.raise_for_status()
            dst.write_bytes(rr.content)

        return dst


    def _fetch_remote_unsure(self):
        """
        Calls GET {API_BASE_URL}/unsure and expects items like:
        {"session_id": "...", "session_path":"...", "pair_id": 42,
        "im1_url":"http://.../images/...", "im2_url":"http://.../images/..."}
        Returns a flat list shaped for FlatPairList.
        """
        url = f"{API_BASE_URL.rstrip('/')}/unsure"
        r = requests.get(url, headers=self._remote_headers(), timeout=API_TIMEOUT)
        r.raise_for_status()
        items = r.json()

        flat = []
        for it in items:
            try:
                im1 = self._cache_get(it["im1_url"])
                im2 = self._cache_get(it["im2_url"])
                flat.append({
                    "session_path": Path(it.get("session_path") or it.get("session_id") or "remote"),
                    "pair_id": int(it["pair_id"]),
                    "im1_path": im1,
                    "im2_path": im2,
                    "unsure_by": it.get("unsure_by") or {},
                    "source": "remote",
                })
            except Exception as e:
                print("[REMOTE] skip item:", e)
        return flat

    def _merge_remote_items(self, items):
        """UI-thread: merge new items and refresh spinner/progress."""
        if not items:
            messagebox.showinfo("Remote", "No remote unsure pairs found.")
            return
        added = self.image_pairs.extend_unique(items)
        # refresh spinner and progress
        self.spinbox.items = self.image_pairs.ids()
        self.spinbox.draw_items()
        self.update_global_progress()
        messagebox.showinfo("Remote", f"Loaded {added} new remote pairs.")

    def _on_load_remote_clicked(self):
        """Fetch in background so UI stays responsive."""
        if not getattr(self, "_flat_mode", False):
            messagebox.showinfo("Remote", "Only available in Unsure mode.")
            return

        # disable during fetch
        self.load_remote_btn.config(state="disabled")
        self.global_progress_label.config(text="Unsure mode — loading remote…")

        def worker():
            try:
                items = self._fetch_remote_unsure()
            except Exception as e:
                err = str(e)
                def fail():
                    self.global_progress_label.config(text="Unsure mode — remote load failed")
                    messagebox.showerror("Remote error", err)
                    self.load_remote_btn.config(state="normal")
                self.after(0, fail)
                return

            def done():
                self._merge_remote_items(items)
                self.load_remote_btn.config(state="normal")
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()




    def refocus_after_button(self):
        self.focus_set()  # Put focus back to main frame (not the button)

    def skip_current_session(self):
        confirm = messagebox.askyesno(
            "Skip Session?",
            "Are you sure you want to mark this session as unusable and skip it?"
        )
        if not confirm:
            return  # User chose to cancel
        
        annotation_path = self.image_pairs.src / "annotations.json"

        data = {}
        if annotation_path.exists():
            with open(annotation_path, "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    print(f"Error decoding {annotation_path}, using empty fallback.")

        data.setdefault("_meta", {})["usable"] = False
        data["_meta"]["completed"] = True

        with open(annotation_path, "w") as f:
            json.dump(data, f, indent=2)

        messagebox.showinfo("Skipped", "Marked session as unusable and moving on.")

        # Move to next session
        if self.session_index + 1 < len(self.session_paths):
            self.session_index += 1
            self.reset(self.session_paths[self.session_index])
            self.load_pair(0)
        else:
            messagebox.showinfo("Done", "All sessions completed.")
            self.quit()
        self.refocus_after_button()

    def flush_cache(self):
        print("[FLUSH] Attempting to upload cached annotations...")
        flush_annotation_cache()
        messagebox.showinfo("Flush Complete", "Cached annotations were flushed to the server (if reachable).")


    def update_global_progress(self):
        # get current pair image names (works for both modes)
        try:
            im1_path, im2_path = self._pair_imgs_at_current()
            im1_name = self._shorten(Path(im1_path).name)
            im2_name = self._shorten(Path(im2_path).name)
            img_pair = f"{im1_name} → {im2_name}"
        except Exception:
            img_pair = ""

        if getattr(self, "_flat_mode", False):
            total_pairs = len(self.image_pairs)
            view_idx = self._flat_view_index + 1
            meta = self.image_pairs.meta_at(self._flat_view_index)
            session_name = Path(meta.get("session_path") or "remote").name
            pair_id = meta["pair_id"]
            self.global_progress_label.config(
                text=f"Unsure mode — {view_idx}/{total_pairs} | {session_name} | pair #{pair_id} | {img_pair}"
            )
            return

        # session mode
        session_name = getattr(self.image_pairs, "src", Path("?")).name
        current_session_number = self.session_index + 1
        total_sessions = len(self.session_paths)
        current_pair = self.current_index + 1
        total_pairs = len(self.image_pairs)
        self.global_progress_label.config(
            text=f"Session {current_session_number}/{total_sessions} — {session_name}: {current_pair}/{total_pairs} | {img_pair}"
        )



    def find_session_paths(self, base_src):
        base = Path(base_src)
        session_paths = []
        for store in sorted(base.glob("store_*")):
            for session in sorted(store.glob("session_*")):
                session_paths.append(session)
        return session_paths

    def setup_key_bindings(self):
        self.master.bind("<Escape>", lambda _: self.quit())
        self.master.bind("<Right>", lambda _: self.right())
        self.master.bind("<f>", lambda _: self.right())
        self.master.bind("<Left>", lambda _: self.left())
        self.master.bind("<s>", lambda _: self.left())
        self.master.bind("<a>", lambda _: self.annotate_btn.invoke())
        self.master.bind("<n>", lambda _: self.nothing_btn.invoke())
        self.master.bind("<c>", lambda _: self.chaos_btn.invoke())
        self.master.bind("<d>", lambda _: self.delete_selected_btn.invoke())
        self.master.bind("<x>", lambda _: self.clear_btn.invoke())
        self.master.bind("<u>", lambda _: self.unsure_btn.invoke())
        self.bind_all("<space>", lambda e: self.toggle_flicker())

        self.focus_set()


    def update_flicker_ui(self, flickering: bool):
        for widget in self.top_right_container.winfo_children():
            widget.pack_forget()

        if flickering:
            self.flicker_label.pack()
        else:
            if getattr(self, "_flat_mode", False):
                # flat/unsure mode: no skip, but show flush + load remote
                self.flush_btn.pack(pady=(4, 0))
                if hasattr(self, "load_remote_btn"):
                    self.load_remote_btn.pack(pady=(4, 0))
            else:
                # session mode: show skip + flush
                self.skip_session_btn.pack()
                self.flush_btn.pack(pady=(4, 0))

    def toggle_flicker(self):
        if not self.flicker_running:
            self.flicker_running = True
            self.flicker_active = False
            self.update_flicker_ui(True)
            self._run_flicker()
            print("Flicker started")
        else:
            self.stop_flicker_if_running()
            # restore right image (static)
            _, right_img = self._pair_imgs_at_current()
            self.image2.load_image(right_img)
            self.image2._resize_image()
            print("Flicker stopped")

    def _run_flicker(self):
        if not self.flicker_running:
            return

        left_img, right_img = self._pair_imgs_at_current()
        # toggle which one we show
        img = left_img if not self.flicker_active else right_img
        self.image2.load_image(img)
        self.image2._resize_image()

        # preserve outline color
        pair_state = self.annotations.get_pair_annotation(self.current_index).get("pair_state")
        color = ImageAnnotation.Classes.PAIR_STATE_COLORS.get(pair_state)
        if color:
            self.image1.draw_canvas_outline(color)
            self.image2.draw_canvas_outline(color)

        self.flicker_active = not self.flicker_active
        # schedule next flip
        self.after(200, self._run_flicker)

    def stop_flicker_if_running(self):
        if self.flicker_running:
            self.flicker_running = False
            self.flicker_active = False
            self.update_flicker_ui(False)
            print("Flicker stopped (auto)")



    def reset(self, src, initial=False):
        print("[RESET] Loading session from:", src)

        self.image_pairs = ImagePairList(src=src)
        self.annotations = ImageAnnotation(base_path=self.image_pairs.src, total_pairs=len(self.image_pairs))
        self.current_index = 0
        self.in_annotation_mode = False

        self.session_index = self.session_paths.index(src)

        # Neue Referenz übergeben
        self.image1.annotation_controller = self.annotations
        self.image2.annotation_controller = self.annotations

        # Spinner nur updaten
        self.spinbox.items = self.image_pairs.ids()
        self.spinbox.current_index = 0
        self.spinbox.draw_items()

        if initial:
            self.load_pair(0)
            self.spinbox.current_index = 0

        # self.load_pair(0)
        self.setup_key_bindings()

        self.update_global_progress()

    def show_reset_message(self):
        dialog = tk.Toplevel(self)
        dialog.title("Reset Complete")
        label = tk.Label(dialog, text="Application has been reset successfully", padx=20, pady=20)
        label.pack()
        dialog.bind("<KeyPress>", lambda e: dialog.destroy())
        dialog.focus_set()  # This is critical - gives keyboard focus to the dialog

    def setup_controls(self):
        """Set up classification and navigation controls"""
        controls = ttk.Frame(self)
        controls.grid(row=2, column=0, columnspan=2, sticky="ew")
        
        
                
        self.nothing_btn = ttk.Button(
            controls, text="Nothing Changed",
            style="Nothing.TButton",
            command=lambda: self.before_action(ImageAnnotation.Classes.NOTHING),
        )

        self.chaos_btn = ttk.Button(
            controls, text="Chaos",
            style="Chaos.TButton",
            command=lambda: self.before_action(ImageAnnotation.Classes.CHAOS)
        )

        self.annotate_btn = ttk.Button(
            controls, text="Annotate",
            style="Annotate.TButton",
            command=lambda: self.before_action(ImageAnnotation.Classes.ANNOTATION)
        )

        self.delete_selected_btn = ttk.Button(
            controls, text="Delete Selected Box",
            style="Delete.TButton",
            command=self.before_delete_selected
        )

        self.clear_btn = ttk.Button(
            controls, text="Reset",
            style="Clear.TButton",
            command=lambda: self.clear_current_boxes(skip=False)
        )

        self.unsure_btn = ttk.Button(
            controls, text="Unsure",
            style="Unsure.TButton",
            command=lambda: self.clear_current_boxes(skip=True)
        )


        self.nothing_btn.pack(side="left", fill="x", expand=True)
        self.chaos_btn.pack(side="left", fill="x", expand=True)
        self.unsure_btn.pack(side="left", fill="x", expand=True)
        self.annotate_btn.pack(side="left", fill="x", expand=True)
        self.delete_selected_btn.pack(side="left", fill="x", expand=True)
        self.clear_btn.pack(side="left", fill="x", expand=True)

        # ⏺️ Speichere Buttons in Liste (außer Clear!)
        self.buttons = [
            self.nothing_btn,
            self.chaos_btn,
            self.annotate_btn,
            self.delete_selected_btn
        ]

    
    def reset_buttons(self):
        """Setzt alle Buttons in unpressed"""
        for btn in self.buttons:
            btn.state(['!pressed'])

    def before_delete_selected(self):
        self.reset_buttons()
        self.toggle_annotation(False)
        self.delete_selected_btn.state(['pressed'])

        # Frage BEIDE Bilder, ob eine Box ausgewählt ist:
        if self.image1.selected_box_index is not None:
            self.image1.delete_selected_box()
        elif self.image2.selected_box_index is not None:
            self.image2.delete_selected_box()
        else:
            print("No box selected in either image.")

            self.image1.selected_box_index = None
            self.image2.selected_box_index = None
        
        # wenn NACH dem Löschen KEINE Boxen mehr existieren → setze pair_state = NO_ANNOTATION
        if not self.image1.get_boxes() and not self.image2.get_boxes():
            new_state = ImageAnnotation.Classes.NO_ANNOTATION
        else:
            new_state = ImageAnnotation.Classes.ANNOTATED

        # self.annotations.save_pair_annotation(
        #     image1=self.image1,
        #     image2=self.image2,
        #     pair_state=new_state
        # )

        self._maybe_save(pair_state=new_state)

        # Optional: Outline anpassen
        self.image1.canvas.delete("canvas_outline")
        self.image2.canvas.delete("canvas_outline")
        if new_state == ImageAnnotation.Classes.NO_ANNOTATION:
            self.image1.draw_canvas_outline("#B497B8")
            self.image2.draw_canvas_outline("#B497B8")

        self.delete_selected_btn.state(['!pressed'])

        self.refocus_after_button()


    def clear_current_boxes(self, skip):
        """Clear all boxes for the current image pair and update JSON"""
        print(f"Clearing boxes for pair {self.current_index}")

        # Anzeige leeren
        self.image1.clear_boxes()
        self.image2.clear_boxes()

        # Daten leeren
        self.image1.boxes = []
        self.image2.boxes = []

        self.image1.clear_mask()
        self.image2.clear_mask()

        self.image1._original_mask_pils = []

        self.image2._original_mask_pils = []
        # Auch in der Annotation leeren & speichern
        boxes1 = self.image1.get_boxes()
        boxes2 = self.image2.get_boxes()

        pair_state = (
            ImageAnnotation.Classes.NO_ANNOTATION
            if not boxes1 and not boxes2
            else ImageAnnotation.Classes.ANNOTATED
        )

        # self.annotations.save_pair_annotation(
        #     # pair_id=self.current_index,  # oder dein pair_id
        #     image1=self.image1,          # das ist AnnotatableImage!
        #     image2=self.image2,          # AnnotatableImage!
        #     pair_state=pair_state
        # )

        self._maybe_save(pair_state=pair_state)

        self.update_ui_state(pair_state=pair_state)
        print(f"Boxes cleared for pair {self.current_index}")
        if skip == True:
            self.right()

        self.refocus_after_button()

    def delete_selected_box(self):
        if self.selected_box_index is None:
            print("No box selected!")
            return

        # Finde die pair_id der ausgewählten Box
        pair_id = self.boxes[self.selected_box_index].get('pair_id')
        print(f"Deleting box pair_id: {pair_id}")

        # Lösche ALLE Boxen mit dieser pair_id in diesem Bild
        self.boxes = [b for b in self.boxes if b.get('pair_id') != pair_id]

        # Gleiche Box auch im anderen Bild löschen:
        other_image = self.controller.image2 if self is self.controller.image1 else self.controller.image1
        other_image.boxes = [b for b in other_image.boxes if b.get('pair_id') != pair_id]

        # Clear & redraw
        self.clear_boxes()
        self.display_boxes(self.boxes)

        other_image.clear_boxes()
        other_image.display_boxes(other_image.boxes)

        self.selected_box_index = None
        other_image.selected_box_index = None
        print("Deleted box in both images.")




    def before_action(self, button_id):
        self.reset_buttons()
        self.state = button_id

        if button_id == ImageAnnotation.Classes.ANNOTATION:
            self.annotate_btn.state(['pressed'])
            self.toggle_annotation(True)
        else:
            self.toggle_annotation(False)
            if button_id == ImageAnnotation.Classes.NOTHING:
                self.nothing_btn.state(['pressed'])
            elif button_id == ImageAnnotation.Classes.CHAOS:
                self.chaos_btn.state(['pressed'])

        self.process_action()
        
        # 🧠 Save current annotation state
        # self.annotations.save_pair_annotation(
        #     image1=self.image1,
        #     image2=self.image2,
        #     pair_state=self.state
        # )

        self._maybe_save(pair_state=self.state)

        # 🎯 CUSTOM UI UPDATE BLOCK
        if button_id in [ImageAnnotation.Classes.CHAOS, ImageAnnotation.Classes.NOTHING]:
            self.image1.clear_boxes()
            self.image2.clear_boxes()
            self.image1.clear_mask()
            self.image2.clear_mask()
            
            # Draw appropriate outline immediately
            if button_id in [ImageAnnotation.Classes.CHAOS, ImageAnnotation.Classes.NOTHING]:
                # Clear visual boxes
                self.image1.clear_boxes()
                self.image2.clear_boxes()

                # Clear actual box data too!
                self.image1.boxes = []
                self.image2.boxes = []

                # Clear masks
                self.image1.clear_mask()
                self.image2.clear_mask()

                # Clear stored masks for safety
                self.image1._original_mask_pils = []
                self.image2._original_mask_pils = []

                # Draw appropriate outline
                if button_id == ImageAnnotation.Classes.CHAOS:
                    outline_color = "orange"
                elif button_id == ImageAnnotation.Classes.NOTHING:
                    outline_color = "#ADD8E6"
                else:
                    outline_color = None

                if outline_color:
                    self.image1.draw_canvas_outline(outline_color)
                    self.image2.draw_canvas_outline(outline_color)
                else:
                    self.image1.canvas.delete("canvas_outline")
                    self.image2.canvas.delete("canvas_outline")

                # self.annotations.save_pair_annotation(
                #     image1=self.image1,
                #     image2=self.image2,
                #     pair_state=self.state
                # )
                self._maybe_save(pair_state=self.state)

        # 🔜 Go to next pair (skip for Annotate mode)
        if button_id != ImageAnnotation.Classes.ANNOTATION:
            print(f"[before_action] Calling right() after classification: {button_id}")
            self.right()

        self.refocus_after_button()

    def process_action(self):
        print("State was set to:", self.state)
    
    def classify(self, classification_type):
        """Save a simple classification and move to next pair"""
        # self.annotations.save_pair_annotation(self.image1, self.image2, classification_type)
        self._maybe_save(pair_state=classification_type)
        self.right()
        # self.load_pair(self.current_index + 1)
    
    def toggle_annotation(self, enabled=None):
        """Schalte Annotation Mode gezielt an/aus"""
        if enabled is None:
            self.in_annotation_mode = not self.in_annotation_mode
        else:
            self.in_annotation_mode = enabled

        self.image1.set_drawing_mode(self.in_annotation_mode)
        self.image2.set_drawing_mode(self.in_annotation_mode)

        if not self.in_annotation_mode:
            self.save_current_boxes()

        self.annotate_btn.state(['pressed'] if self.in_annotation_mode else ['!pressed'])

    def annotation_off(self):
        self.in_annotation_mode = False
        self.annotate_btn.state(['!pressed'])
        self.image1.set_drawing_mode(False)
        self.image2.set_drawing_mode(False)
        self.save_current_boxes()
        self.image1.clear_boxes()
        self.image2.clear_boxes()
        self.right()


    def _pair_imgs_at_current(self):
        if getattr(self, "_flat_mode", False):
            return self.image_pairs[self._flat_view_index]
        return self.image_pairs[self.current_index]

    @property
    def current_id(self):
        im1_path, im2_path = self._pair_imgs_at_current()
        return (im1_path, im2_path)


    def save_current_boxes(self):
        all_boxes = self.image1.get_boxes() + self.image2.get_boxes()
        boxes_to_save = [b for b in all_boxes if not b.get("synced_highlight")]

        if not boxes_to_save:
            return
        # self.annotations.save_pair_annotation(self.image1, self.image2, ImageAnnotation.Classes.ANNOTATED)

        self._maybe_save(pair_state=ImageAnnotation.Classes.ANNOTATED)

    def load_pair(self, index):
        print("load pair called")

        self.stop_flicker_if_running()

        if self.in_annotation_mode:
            print("Was in annotation mode, toggling off")
            self.annotation_off()

        # --- Flat/Unsure-Mode? ---
        if getattr(self, "_flat_mode", False):
            self._flat_view_index = index
            self.spinbox.current_index = index

            meta = self.image_pairs.meta_at(index)
            session_path = meta["session_path"]
            original_pair_id = int(meta["pair_id"])

            # Annotation-Controller auf die richtige Session schalten
            if self.annotations is None or str(self.annotations.base_path) != str(session_path):
                self.annotations = ImageAnnotation(base_path=session_path, total_pairs=None)

            # WICHTIG: current_index = ORIGINAL pair_id der Session (für JSON)
            self.current_index = original_pair_id

            # Bilder laden
            img1, img2 = self.image_pairs[index]
            self.image1.canvas.delete("canvas_outline")
            self.image2.canvas.delete("canvas_outline")
            self.image1.clear_all(); self.image2.clear_all()
            self.image1.load_image(img1); self.image2.load_image(img2)
            self.image1._resize_image(); self.image2._resize_image()

            # Annotation rehydrieren (gleich wie dein Session-Code)
            annotation = self.annotations.get_pair_annotation(self.current_index)
            boxes = annotation.get("boxes", [])

            # 🔁 Falls es in unsure_reviews.json einen neueren Eintrag gibt, priorisieren
            unsure_entry = self._get_unsure_entry(session_path, original_pair_id)
            if unsure_entry:
                # Boxes & State aus globaler Datei übernehmen
                boxes = unsure_entry.get("boxes", boxes)
                if unsure_entry.get("pair_state") is not None:
                    annotation["pair_state"] = unsure_entry["pair_state"]
            else:
                # Kein Eintrag im globalen Log → Standard 'no_annotation'
                annotation.setdefault("pair_state", ImageAnnotation.Classes.NO_ANNOTATION)


            self.image1._original_mask_pils = []; self.image2._original_mask_pils = []
            image1_boxes, image2_boxes = [], []

            for box in boxes:
                b = dict(box)
                if b["annotation_type"] == ImageAnnotation.Classes.ANNOTATION_X:
                    image1_boxes.append(b)
                    m = b.copy(); m["annotation_type"] = ImageAnnotation.Classes.ANNOTATION; m["synced_highlight"] = True
                    image2_boxes.append(m)
                    if "mask_base64" in b:
                        self.image1._original_mask_pils.append(Image.open(io.BytesIO(base64.b64decode(b["mask_base64"]))).convert("RGBA"))
                elif b["annotation_type"] == ImageAnnotation.Classes.ANNOTATION:
                    image2_boxes.append(b)
                    m = b.copy(); m["annotation_type"] = ImageAnnotation.Classes.ANNOTATION_X; m["synced_highlight"] = True
                    image1_boxes.append(m)
                    if "mask_base64" in b:
                        self.image2._original_mask_pils.append(Image.open(io.BytesIO(base64.b64decode(b["mask_base64"]))).convert("RGBA"))

            self.image1.boxes = image1_boxes
            self.image2.boxes = image2_boxes
            self.image1.display_boxes(image1_boxes)
            self.image2.display_boxes(image2_boxes)
            self.image1.display_mask()
            self.image2.display_mask()

            pair_state = annotation.get("pair_state")
            self.update_global_progress()
            self.after_idle(lambda: self.update_ui_state(pair_state))
            return  # wichtig: Session-Zweig unten überspringen


        self.current_index = index
        self.spinbox.current_index = index

        if 0 <= index < len(self.image_pairs):
            self.current_index = index
            img1, img2 = self.image_pairs[index]

            self.image1.canvas.delete("canvas_outline")
            self.image2.canvas.delete("canvas_outline")

            # 1) Alles leeren
            self.image1.clear_all()
            self.image2.clear_all()

            # 2) Bilder neu laden
            self.image1.load_image(img1)
            self.image2.load_image(img2)


            self.image1._resize_image()
            self.image2._resize_image()

            # 3) Annotation laden
            annotation = self.annotations.get_pair_annotation(index)
            print("annotation pair_state:", annotation.get("pair_state"))
            # print("annotation object:", annotation)
            short_annotation = copy.deepcopy(annotation)

            for box in short_annotation.get("boxes", []):
                if "mask_base64" in box:
                    box["mask_base64"] = box["mask_base64"][:10] + "..."

            print("annotation object:", short_annotation)
            boxes = annotation.get("boxes", [])

            self.image1._original_mask_pils = []
            self.image2._original_mask_pils = []

            image1_boxes = []
            image2_boxes = []
            image1_mirrored_boxes = []
            image2_mirrored_boxes = []

            for box in boxes:
                box_copy = dict(box)


                if box["annotation_type"] == ImageAnnotation.Classes.ANNOTATION_X:
                    # Originalbox auf image1
                    image1_boxes.append(box_copy)
                    mirror = box_copy.copy()
                    mirror["annotation_type"] = ImageAnnotation.Classes.ANNOTATION
                    mirror["synced_highlight"] = True
                    if "mask_base64" in box:
                        mask_bytes = base64.b64decode(box["mask_base64"])
                        mask_pil = Image.open(io.BytesIO(mask_bytes)).convert("RGBA")
                        self.image1._original_mask_pils.append(mask_pil)

                    # Gegenstück visuell auf image2
                    image2_boxes.append(mirror)  # optional gespiegelt

                elif box["annotation_type"] == ImageAnnotation.Classes.ANNOTATION:
                    # Originalbox auf image2
                    image2_boxes.append(box_copy)
                    mirror = box_copy.copy()
                    mirror["annotation_type"] = ImageAnnotation.Classes.ANNOTATION_X
                    mirror["synced_highlight"] = True

                    if "mask_base64" in box:
                        mask_bytes = base64.b64decode(box["mask_base64"])
                        mask_pil = Image.open(io.BytesIO(mask_bytes)).convert("RGBA")
                        self.image2._original_mask_pils.append(mask_pil)

                    # Gegenstück visuell auf image1

                    image1_boxes.append(mirror)

            self.image1.boxes = image1_boxes
            self.image2.boxes = image2_boxes

            # Anzeige leicht verzögert
            def draw_all():
                self.image1.display_boxes(image1_boxes)
                self.image2.display_boxes(image2_boxes)

                self.update_ui_state(pair_state)

            self.after(200, draw_all)


            self.image1.display_mask()
            self.image2.display_mask()

            pair_state = annotation.get("pair_state")

            if pair_state == ImageAnnotation.Classes.NO_ANNOTATION:
                color = "#B497B8" 
            elif pair_state == ImageAnnotation.Classes.CHAOS:
                color = "orange"
            elif pair_state == ImageAnnotation.Classes.NOTHING:
                color = "#add8e6"
            else:
                color = None  # keine Outline

            self.update_global_progress()

            self.after_idle(lambda: self.update_ui_state(pair_state))


        if self.end_of_set:
            print("End of image pairs")





    @property
    def end_of_set(self):
        if getattr(self, "_flat_mode", False):
            return self._flat_view_index == len(self.image_pairs) - 1
        return self.current_index == len(self.image_pairs) - 1



    def update_ui_state(self, pair_state):
        if pair_state is None:
            pair_state = ImageAnnotation.Classes.NO_ANNOTATION
        color = ImageAnnotation.Classes.PAIR_STATE_COLORS.get(pair_state)
        self._current_outline_color = color  # <<< remember current outline
        # draw (will also be re-drawn by resize hook below)
        self.redraw_outline()
        print(f"[UI] Updating canvas outline for state: {pair_state}")



    def right(self):
        print(f"[RIGHT] current_index = {self.current_index}")
        self.reset_buttons() 
        self.save_current_boxes()  # 🔧 DAS HIER HINZUFÜGEN


        # Speichern als 'no_annotation', falls keine Annotation gesetzt wurde
        annotation = self.annotations.get_pair_annotation(self.current_index)
        pair_state = annotation.get("pair_state")
        boxes_exist = bool(self.image1.get_boxes() or self.image2.get_boxes())

        if pair_state == None:
            if boxes_exist:
                pair_state = ImageAnnotation.Classes.ANNOTATED
            else:
                pair_state = ImageAnnotation.Classes.NO_ANNOTATION
            
            print(f"[AUTO] setting default state: {pair_state}")
            # self.annotations.save_pair_annotation(
            #     self.image1,
            #     self.image2,
            #     pair_state=pair_state
            # )
            self._maybe_save(pair_state=pair_state)

            print(f"[AUTO-SAVE-RIGHT] Marked pair {self.current_index} as {pair_state}")

        if getattr(self, "_flat_mode", False):
            # Standardzustand setzen falls None
            annotation = self.annotations.get_pair_annotation(self.current_index)
            pair_state = annotation.get("pair_state")
            boxes_exist = bool(self.image1.get_boxes() or self.image2.get_boxes())
            if pair_state is None:
                pair_state = ImageAnnotation.Classes.ANNOTATED if boxes_exist else ImageAnnotation.Classes.NO_ANNOTATION
                # self.annotations.save_pair_annotation(self.image1, self.image2, pair_state=pair_state)
                self._maybe_save(pair_state=pair_state)

            if self._flat_view_index + 1 < len(self.image_pairs):
                self.load_pair(self._flat_view_index + 1)
            else:
                messagebox.showinfo("Done", "All unsure pairs reviewed.")
                self.quit()
            return


        ret = self.spinbox.animate_scroll(+1)

        if ret == HorizontalSpinner.ReturnCode.END_RIGHT:
            if self.session_index + 1 < len(self.session_paths):
                self.session_index += 1
                next_session = self.session_paths[self.session_index]

                
                messagebox.showinfo(
                    "Session complete",
                    "Load next session"
                )
                # self.image1._resize_image()
                # self.image2._resize_image()
                self.reset(next_session)
                self.load_pair(0)
            else:
                messagebox.showinfo("Done", "All sessions completed.")
                self.quit()

    def left(self):
        print(f"[LEFT] current_index = {self.current_index}")
        # Speichern vor Verlassen
        self.reset_buttons() 
        annotation = self.annotations.get_pair_annotation(self.current_index)
        if not annotation or not annotation.get("pair_state"):
            # self.annotations.save_pair_annotation(
            #     self.image1,
            #     self.image2,
            #     pair_state=ImageAnnotation.Classes.NO_ANNOTATION
            # )
            self._maybe_save(pair_state=ImageAnnotation.Classes.NO_ANNOTATION)

        print(f"[AUTO-SAVE-LEFT] Marked pair {self.current_index} as NO_ANNOTATION")

        if getattr(self, "_flat_mode", False):
            annotation = self.annotations.get_pair_annotation(self.current_index)
            if not annotation or not annotation.get("pair_state"):
                # self.annotations.save_pair_annotation(self.image1, self.image2, pair_state=ImageAnnotation.Classes.NO_ANNOTATION)
                self._maybe_save(pair_state=ImageAnnotation.Classes.NO_ANNOTATION)
            if self._flat_view_index > 0:
                self.load_pair(self._flat_view_index - 1)
            else:
                messagebox.showinfo("Start", "Already at first unsure pair.")
            return

        ret = self.spinbox.animate_scroll(-1)

        if ret == HorizontalSpinner.ReturnCode.END_LEFT:
            if self.session_index > 0:
                self.session_index -= 1
                prev_session = self.session_paths[self.session_index]
                messagebox.showinfo(
                    "Back to previous session",
                    "Jump back to previous session."
                )
                self.reset(prev_session)

                last_idx = len(self.image_pairs) - 1
                self.current_index = last_idx
                self.spinbox.current_index = last_idx
                self.spinbox.draw_items()
                self.load_pair(last_idx)
                # self.image1._resize_image()
                # self.image2._resize_image()
            else:
                print("[LEFT] Already at first session.")
                messagebox.showinfo(
                    "Cannot skip back",
                    "Already at first session."
                )




    def set_images(self, idx):
        self.load_pair(idx)


if __name__ == "__main__":
    app = PairViewerApp()
    app.mainloop()