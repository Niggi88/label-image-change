from pathlib import Path
from PIL import Image
from dataclasses import dataclass
from src.logic_annotation.logic_saver import AnnotationSaver



class AnnotatableImage:
    def __init__(self, img_path, image_id):
        self.img_path = Path(img_path)
        self.img_name = self.img_path.name
        self.img_size = Image.open(self.img_path).size if self.img_path.exists() else None
        self.boxes = []
        self.image_id = image_id




class ImagePair:
    def __init__(self, pair_id, img1_path, img2_path):

        self.pair_id = pair_id
        self.image1 = AnnotatableImage(img1_path, image_id=1)
        self.image2 = AnnotatableImage(img2_path, image_id=2)

        self.pair_annotation = None

    def update_pair_annotation(self, state: str):
        self.pair_annotation = state

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



class DataHandler:
    def __init__(self, dataset_dir, skip_completed=False):
        self.dataset_dir = dataset_dir
        self.all_sessions = SessionList(self.dataset_dir, skip_completed=skip_completed)

        self.pairs = None
        self.total_pairs = None

        self._load_current_session_pairs()

        self.saver = AnnotationSaver(self.current_session_info())

    def _load_current_session_pairs(self):
        info = self.all_sessions.current()
        self.pairs = ImagePairList(info.path)
        self.total_pairs = len(self.pairs)
        if not len(self.pairs):
            print(f"Warning: session {info.session} has no pairs")


    def current_pair(self):
        return self.pairs.current()
    
    def current_session_info(self):
        return self.all_sessions.current()
    

    def next_pair(self):
        next = self.pairs.next()
        # next pair if it exists
        if next: return next

        # when last pair in session -> session over
        if self.all_sessions.next():
            print("start next session")
            self._load_current_session_pairs()
            self.saver = AnnotationSaver(self.current_session_info())
            return self.pairs.first() if len(self.pairs) else None
        
        return None
    

    def prev_pair(self):
        prv = self.pairs.prev()
        if prv: return prv
        if self.all_sessions.prev():
            print("go back to previous session")
            self._load_current_session_pairs()
            self.saver = AnnotationSaver(self.current_session_info())
            return self.pairs.last() if len(self.pairs) else None
        return None  # start of all data
    

    def has_next_pair_global(self):
        return self.pairs.has_next() or self.all_sessions.has_next()

    def has_prev_pair_global(self):
        return self.pairs.has_prev() or self.all_sessions.has_prev()
    
    def skip_current_session(self):
        """Mark current session as unusable in its annotations.json."""
        info = self.current_session_info()
        saver = AnnotationSaver(info)

        if "_meta" not in saver.annotations:
            saver.annotations["_meta"] = {}

        saver.annotations["_meta"]["usable"] = False
        saver._flush()

        print(f"Session {info.session} marked as unusable.")
        # direkt zur nächsten Session springen
        if self.all_sessions.has_next():
            self.all_sessions.next()
            self._load_current_session_pairs()
            self.saver = AnnotationSaver(self.current_session_info())