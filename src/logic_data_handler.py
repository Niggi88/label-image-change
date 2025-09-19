from pathlib import Path
from PIL import Image
from dataclasses import dataclass




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
    def __init__(self, dataset_dir):
        self.dataset_dir = Path(dataset_dir)
        self.sessions = self.append_sessions()
        self.session_idx = 0

    def append_sessions(self):
        sessions = []
        for store in sorted(self.dataset_dir.glob("store_*")):
            for session in sorted(store.glob("session_*")):
                sessions.append(SessionInfo(store=store.name, session=session.name, path=session)) 
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
    def __init__(self, dataset_dir):
        self.dataset_dir = dataset_dir
        self.all_sessions = SessionList(self.dataset_dir)

        self.pairs = None
        self._load_current_session_pairs()

    def _load_current_session_pairs(self):
        info = self.all_sessions.current()
        self.pairs = ImagePairList(info.path)
        if not len(self.pairs):
            print(f"⚠️ Warning: session {info.session} has no pairs")


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
            self._load_current_session_pairs()
            return self.pairs.first() if len(self.pairs) else None
        
        return None
    

    def prev_pair(self):
        prv = self.pairs.prev()
        if prv: return prv
        if self.all_sessions.prev():
            self._load_current_session_pairs()
            return self.pairs.last() if len(self.pairs) else None
        return None  # start of all data
    

    def has_next_pair_global(self):
        return self.pairs.has_next() or self.all_sessions.has_next()

    def has_prev_pair_global(self):
        return self.pairs.has_prev() or self.all_sessions.has_prev()