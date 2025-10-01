from pathlib import Path
from PIL import Image
from dataclasses import dataclass
from src.logic_annotation.logic_saver import AnnotationSaver, InconsistentSaver, UnsureSaver
from abc import ABC, abstractmethod
from src.config import LOCAL_LOG_DIR, USERNAME
from io import BytesIO
from urllib.parse import urljoin
import requests
import json
from tkinter import messagebox


class BaseDataHandler(ABC):
    """
    Abstract interface for data handlers.
    Both SessionDataHandler and BatchDataHandler must implement these methods.
    """

    @abstractmethod
    def current_pair(self):
        """Return the current ImagePair."""
        pass

    @abstractmethod
    def next_pair(self):
        """Move to the next pair and return it."""
        pass

    @abstractmethod
    def prev_pair(self):
        """Move to the previous pair and return it."""
        pass

    @abstractmethod
    def has_next_pair_global(self) -> bool:
        """Return True if there is another pair after the current one."""
        pass

    @abstractmethod
    def has_prev_pair_global(self) -> bool:
        """Return True if there is another pair before the current one."""
        pass

    def has_next_pair_in_scope():
        pass

    @abstractmethod
    def load_current_pairs(self):
        """
        Load the pairs relevant to the current context 
        (e.g. session or batch).
        """
        pass

    @abstractmethod
    def context_info(self):
        pass

    @abstractmethod
    def current_session_index(self):
        """Return (current_idx, total, session_name) or None if not applicable."""
        return None

    @abstractmethod
    def ask_upload(self):
        pass


class AnnotatableImage:
    def __init__(self, img_path, image_id):
        self.img_path = Path(img_path)
        self.img_name = self.img_path.name
        self.img_size = Image.open(self.img_path).size if self.img_path.exists() else None
        self.boxes = []
        self.image_id = image_id


class RemoteAnnotatableImage(AnnotatableImage):
    """For API-served images (http/https)."""
    def __init__(self, url: str, image_id: int, api_base: str = None):
        self.url = url if url.startswith("http") else f"{api_base.rstrip('/')}/{url.lstrip('/')}"
        self.img_name = Path(url).name
        self.img_path = None  # no local path
        self.boxes = []
        self.image_id = image_id
        self._img_size = None  # lazy loaded

    @property
    def img_size(self):
        if self._img_size is None:
            pil_img = self.load_image()
            self._img_size = pil_img.size
        return self._img_size

    def load_image(self):
        resp = requests.get(self.url, timeout=30)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    

class ImagePair:
    def __init__(self, pair_id, img1_path, img2_path, remote=False, api_base=None):
        self.pair_id = pair_id
        if remote:
            self.image1 = RemoteAnnotatableImage(img1_path, image_id=1, api_base=api_base)
            self.image2 = RemoteAnnotatableImage(img2_path, image_id=2, api_base=api_base)
        else:
            self.image1 = AnnotatableImage(img1_path, image_id=1)
            self.image2 = AnnotatableImage(img2_path, image_id=2)

        self.pair_annotation = None

    def update_pair_annotation(self, state: str):
        self.pair_annotation = state


class BatchImagePairList:
    """Wrapper around a list of ImagePairs for batch mode, with same API as ImagePairList."""

    def __init__(self, image_pairs):
        self.image_pairs = image_pairs
        self.pair_idx = 0

    def current(self):
        return self.image_pairs[self.pair_idx]

    def has_next(self):
        return self.pair_idx < len(self.image_pairs) - 1

    def has_prev(self):
        return self.pair_idx > 0

    def next(self):
        if self.has_next():
            self.pair_idx += 1
            return self.current()
        return None

    def prev(self):
        if self.has_prev():
            self.pair_idx -= 1
            return self.current()
        return None

    def first(self):
        self.pair_idx = 0
        return self.current() if self.image_pairs else None

    def last(self):
        self.pair_idx = len(self.image_pairs) - 1
        return self.current() if self.image_pairs else None

    def __len__(self):
        return len(self.image_pairs)


class ImagePairList:
    '''
    holds a list of ImagePair instances for one session each
    '''
    def __init__(self, session_path):
        self.session_path = session_path
        self.images = sorted(self.session_path.glob("*.jpeg"), key=lambda f: int(f.name.split("-")[0]))
        
        self.image_pairs = [
            ImagePair(idx, self.images[idx], self.images[idx + 1])
            for idx in range(len(self.images) - 1)
        ]

        self.pair_idx = 0

    def current(self):
        return self.image_pairs[self.pair_idx]

    def has_next(self):
        return self.pair_idx < len(self.image_pairs) - 1

    def has_prev(self):
        return self.pair_idx > 0
    

    def next(self):
        if self.has_next():
            self.pair_idx += 1
            return self.current()
        return None
    
    def prev(self):
        if self.has_prev():
            self.pair_idx -= 1
            return self.current()
        return None
    
    
    def first(self):
        self.pair_idx = 0
        return self.current() if self.image_pairs else None

    def last(self):
        self.pair_idx = len(self.image_pairs) - 1
        return self.current() if self.image_pairs else None

    def __len__(self):
        return len(self.image_pairs)
        

@dataclass
class SessionInfo:
    store: str
    session: str
    path: Path

class SessionList:
    def __init__(self, dataset_dir, skip_completed=False):
        self.dataset_dir = Path(dataset_dir)
        self.sessions = self.append_sessions(skip_completed=skip_completed)
        self.session_idx = 0

    def append_sessions(self, skip_completed=False):
        sessions = []
        for store in sorted(self.dataset_dir.glob("store_*")):
            for session in sorted(store.glob("session_*")):
                info = SessionInfo(store=store.name, session=session.name, path=session)

                if skip_completed:
                    ann_file = session / "annotations.json"
                    if ann_file.exists():
                        import json
                        try:
                            with open(ann_file, "r") as f:
                                data = json.load(f)
                            meta = data.get("_meta", {})
                            completed = meta.get("completed", False)
                            usable = meta.get("usable", True)
                            if completed or not usable:
                                continue
                        except Exception as e:
                            print(f"Warning: could not read {ann_file}: {e}")

                sessions.append(info)
        return sessions


    def current(self):
        return self.sessions[self.session_idx]
    
    def has_next(self):
        return self.session_idx < len(self.sessions) - 1

    def has_prev(self):
        return self.session_idx > 0
    

    def next(self):
        if self.has_next():
            self.session_idx += 1
            return self.current()
        return None
    
    def prev(self):
        if self.has_prev():
            self.session_idx -= 1
            return self.current()
        return None
    
    def __len__(self): return len(self.sessions)



class SessionDataHandler(BaseDataHandler):
    def __init__(self, dataset_dir, api_base, skip_completed=False):
        self.dataset_dir = dataset_dir
        self.api_base = api_base.rstrip("/")
        
        self.all_sessions = SessionList(self.dataset_dir, skip_completed=skip_completed)

        self.pairs = None
        self.total_pairs = None

        self.load_current_pairs()

        self.saver = AnnotationSaver(self.current_session_info())

    def load_current_pairs(self):
        info = self.all_sessions.current()
        self.pairs = ImagePairList(info.path)
        self.total_pairs = len(self.pairs)
        if not len(self.pairs):
            print(f"Warning: session {info.session} has no pairs")

    def current_session_index(self):
        return (
            self.all_sessions.session_idx,
            len(self.all_sessions),
            self.current_session_info().session
        )

    def current_pair(self):
        return self.pairs.current()
    
    def current_session_info(self):
        return self.all_sessions.current()
    
    def context_info(self):
        return self.current_session_info()

    def next_pair(self):
        next = self.pairs.next()
        # next pair if it exists
        if next: return next

        # when last pair in session -> session over
        if self.all_sessions.next():
            print("start next session")
            self.load_current_pairs()
            self.saver = AnnotationSaver(self.current_session_info())
            return self.pairs.first() if len(self.pairs) else None
        
        return None
    

    def prev_pair(self):
        prv = self.pairs.prev()
        if prv: return prv
        if self.all_sessions.prev():
            print("go back to previous session")
            self.load_current_pairs()
            self.saver = AnnotationSaver(self.current_session_info())
            return self.pairs.last() if len(self.pairs) else None
        return None  # start of all data
    

    def has_next_pair_global(self):
        return self.pairs.has_next() or self.all_sessions.has_next()

    def has_prev_pair_global(self):
        return self.pairs.has_prev() or self.all_sessions.has_prev()
    

    def has_next_pair_in_scope(self):
        return self.pairs.has_next()

    def skip_current_session(self):
        """Mark current session unusable and move to the next if available."""
        self.saver.mark_session_unusable()
        print(f"Session {self.current_session_info().session} marked as unusable.")

        if self.all_sessions.has_next():
            self.all_sessions.next()
            self.load_current_pairs()
            self.saver = AnnotationSaver(self.current_session_info())


    def context_info(self):
        return {
            "progress": {
                "current_pair_index": self.pairs.pair_idx + 1,
                "current_session_index":self.all_sessions.session_idx + 1,
                "total": len(self.pairs),
                "label": self.current_session_info().session,
            },
            "session_info": self.current_session_info()
        }

    @property
    def mode(self):
        return "annotation"

    def get_status_text(self):
        # always Pair X/Y
        return f"Pair {self.pairs.pair_idx+1}/{len(self.pairs)}"

    def get_session_text(self):
        return (
            f"Session {self.all_sessions.session_idx+1}/{len(self.all_sessions)} "
            f"– {self.current_session_info().session}"
        )
    
    def upload_results(self, results: dict = None):
        """
        Upload the annotations.json for the current session.
        """
        ann_file = self.saver.file
        if not ann_file.exists():
            raise RuntimeError("No annotations.json to upload")
        
        with open(ann_file, "r") as f:
            data = json.load(f)
        
        info = self.current_session_info()
        session_id = f"{info.store}_{info.session}"

        try:
            with open(ann_file, 'rb') as f:
                files = {'file': (f"{session_id}.json", f)}
                data = {
                    'username': USERNAME,
                    'session_id': session_id
                }
                path = f"results/annotations"
                url = urljoin(self.api_base + "/", path.lstrip("/"))
                response = requests.post(url, files=files, data=data)
                if response.status_code == 200:
                    print(f"✅ Uploaded {session_id}.json")
                else:
                    print(f"❌ Failed to upload {session_id}.json — Status {response.status_code}")
                    print(response.text)
        except Exception as e:
            print(f"💥 Error uploading {ann_file}: {e}")

        response.raise_for_status()
        return response.json()
    

    def upload_images(self):
        """
        Upload all images for the current session to the API.
        Uses the /upload_image endpoint on the server.
        """
        info = self.current_session_info()

        # loop through all pairs in the session
        for pair in self.pairs.image_pairs:
            for img in (pair.image1, pair.image2):
                if img.img_path and img.img_path.exists():
                    # relative path inside dataset_dir (so server can place it correctly)
                    relative_path = str(img.img_path.relative_to(self.dataset_dir))
                    try:
                        with open(img.img_path, "rb") as f:
                            files = {"file": (img.img_name, f)}
                            data = {"relative_path": relative_path}
                            url = f"{self.api_base.rstrip('/')}/upload_image"
                            resp = requests.post(url, files=files, data=data, timeout=30)
                            resp.raise_for_status()
                            print(f"✅ Uploaded image {relative_path}")
                    except Exception as e:
                        print(f"❌ Failed to upload {img.img_path}: {e}")
        

    def ask_upload(self) -> bool:
            confirm = messagebox.askyesno(
                "Session finished",
                f"Session {self.current_session_index()} is complete.\n\nDo you want to upload your annotations now?"
            )
            if not confirm:
                return False

            try:
                self.upload_results()  # will send annotations.json
                self.upload_images()
                messagebox.showinfo("Upload complete", "Session uploaded successfully.")
                return True
            except Exception as e:
                messagebox.showerror("Upload failed", f"Something went wrong:\n{e}")
                return False
    

class BatchDataHandler(BaseDataHandler):
    """
    Gemeinsame Logik für Batch-basierte Review Modi (unsure, inconsistent).
    Holt Paare vom API-Server in Batches und erlaubt Navigation.
    """

    def __init__(self, api_base: str, batch_type: str, user: str, size: int = 5, saver_cls=None):
        self.api_base = api_base.rstrip("/")
        self.batch_type = batch_type
        self.user = user
        self.size = size
        self.saver = None  # attach later
        self.saver_cls = saver_cls

        self.pairs = []
        self.idx = 0
        self.batch_id = None
        self.meta = {}

        self.load_current_pairs()

    def load_current_pairs(self):
        """Fetch a new batch from the API and wrap into BatchImagePairList."""
        path = f"/batch/{self.batch_type}"
        url = urljoin(self.api_base + "/", path.lstrip("/"))
        resp = requests.get(url, params={"user": self.user, "size": self.size}, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        self.batch_id = data.get("batch_id")
        self.meta = data

        pairs = []
        for key, item in (data.get("items") or {}).items():
            pair = ImagePair(
                pair_id=item["pair_id"],
                img1_path=item["im1_url"],
                img2_path=item["im2_url"],
                remote=True,
                api_base=self.api_base
            )
            pair.expected = item.get("expected")
            pair.predicted = item.get("predicted")
            pair.annotated_by = item.get("annotated_by")
            pair.model_name = item.get("model_name")
            pair.source_item = item
            pairs.append(pair)

        # Wrap in BatchImagePairList
        self.pairs = BatchImagePairList(pairs)
        print("Loaded batch with", len(self.pairs), "pairs, starting at index", self.pairs.pair_idx)


    # --- Delegate to BatchImagePairList instead of indexing ---
    def current_pair(self):
        return self.pairs.current() if self.pairs else None

    def next_pair(self):
        return self.pairs.next() if self.pairs else None

    def prev_pair(self):
        return self.pairs.prev() if self.pairs else None

    def has_next_pair_global(self) -> bool:
        return self.pairs.has_next() if self.pairs else False

    def has_prev_pair_global(self) -> bool:
        return self.pairs.has_prev() if self.pairs else False


    def has_next_pair_in_scope(self):
            return self.has_next_pair_global()



    def current_session_index(self):
        return None  # no sessions in review mode
    
    def context_info(self):
        return {
            "progress": {
                "current_pair_index": self.pairs.pair_idx + 1 if self.pairs else 0,
                "current_session_index": None,
                "total": len(self.pairs),
                "label": f"Batch {self.batch_id}" if self.batch_id else "Batch",
            },
            "batch_meta": self.meta,
            "user": self.user,
        }
    
    @property
    def mode(self):
        return "review"

    def get_status_text(self):
        return f"Pair {self.pairs.pair_idx+1}/{len(self.pairs)}"


    def get_session_text(self):
        """
        To be implemented by subclasses (UnsureDataHandler, InconsistentDataHandler).
        """
        return ""
    
    # ------------------------------
    # Review-spezifische Funktion
    # ------------------------------

    def upload_results(self, results: dict):
        """
        Ergebnisse für das Batch hochladen.
        results: Dict[str, Any], keys = "store_session_path|pair_id"
        """
        if not self.batch_id:
            raise RuntimeError("Kein aktives Batch geladen")

        path = f"/batches/{self.batch_id}/results"
        url = urljoin(self.api_base + "/", path.lstrip("/"))
        resp = requests.post(url, json=results, timeout=30)
        resp.raise_for_status()
        return resp.json()
    
    def ask_upload(self):
            confirm = messagebox.askyesno(
                "Batch finished",
                "You have reached the end of this batch.\n\nDo you want to upload your results now?"
            )
            if not confirm:
                return False

            try:
                results = self.saver.annotations
                self.upload_results(results)
                messagebox.showinfo("Upload complete", "Batch has been uploaded and marked completed.")
                self.load_current_pairs()  # fetch fresh batch
                return True
            except Exception as e:
                messagebox.showerror("Upload failed", f"Something went wrong:\n{e}")
                return False

# ------------------------------
# Spezialisierungen
# ------------------------------

class UnsureDataHandler(BatchDataHandler):
    def __init__(self, api_base: str, user: str, size: int = 20):
        super().__init__(api_base, "unsure", user, size, saver_cls=UnsureSaver)
        self.saver = UnsureSaver(self.meta, LOCAL_LOG_DIR)


    def get_session_text(self):
        pair = self.current_pair()
        key = f"{pair.source_item['store_session_path']}|{pair.pair_id}"
        ann = self.saver.annotations["items"].get(key, {})

        annotated_by = ann.get("unsure_by")
        if not annotated_by and "items" in self.meta:
            ann = self.meta["items"].get(f"{pair.source_item['store_session_path']}|{pair.pair_id}", {})
            annotated_by = ann.get("unsure_by")

        if isinstance(annotated_by, dict):
            annotated_by = annotated_by.get("name")

        return (
            f"Batch ID: {self.batch_id}"
            f"\nAnnotated by: {annotated_by or 'unknown'}"
        )



class InconsistentDataHandler(BatchDataHandler):
    def __init__(self, api_base: str, user: str, size: int = 20):
        super().__init__(api_base, "inconsistent", user, size, saver_cls=InconsistentSaver)
        self.saver = InconsistentSaver(self.meta, LOCAL_LOG_DIR)

    def get_session_text(self):
        pair = self.current_pair()
        ann = self.saver.annotations["items"].get(str(pair.pair_id), {})

        reviewed_by = ann.get("reviewed_by")
        if isinstance(reviewed_by, dict):
            reviewed_by = reviewed_by.get("name")

        # fallback: check server meta
        if not ann and "items" in self.meta:
            ann = self.meta["items"].get(f"{pair.source_item['store_session_path']}|{pair.pair_id}", {})
            reviewed_by = ann.get("reviewed_by")

        return (
            f"Batch ID: {self.batch_id}"
            f"\nExpected: {ann.get('expected')} "
            f"by: {reviewed_by or 'unknown'}"
            f"\nPredicted: {ann.get('predicted')} "
            f"by model: {ann.get('model_name')}"
        )
