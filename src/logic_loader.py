from pathlib import Path
from PIL import Image


class DataHandler:
    def __init__(self, dataset_dir):
        self.dataset_dir = Path(dataset_dir)
        self.sessions = self.find_session_paths(self.dataset_dir)

        if not self.sessions:
            raise ValueError(f"No sessions found under {dataset_dir}")

        self.session_index = 0
        self.loader = PairLoader(str(self.sessions[self.session_index]["path"]))

    def find_session_paths(self, base_dir):
        """Scan dataset dir for all store/session combinations."""
        sessions = []
        for store in sorted(base_dir.glob("store_*")):
            for session in sorted(store.glob("session_*")):
                sessions.append({
                    "store": store.name,
                    "session": session.name,
                    "path": session
                })
        return sessions

    # --- Accessors ---
    def current_loader(self):
        return self.loader

    def current_session_info(self):
        return self.sessions[self.session_index]

    # --- Navigation ---
    def next_session(self):
        if self.session_index < len(self.sessions) - 1:
            self.session_index += 1
            self.loader = PairLoader(str(self.sessions[self.session_index]["path"]))
            print("load next session")
            return True
        return False

    def prev_session(self):
        if self.session_index > 0:
            self.session_index -= 1
            self.loader = PairLoader(str(self.sessions[self.session_index]["path"]))
            print("load previous session")
            return True
        return False



class AnnotatableImage:
    def __init__(self, img_path, image_id):
        self.img_path = Path(img_path)
        self.img_size = Image.open(self.img_path).size if self.img_path.exists() else None
        self.boxes = []
        self.image_id = image_id 


class ImagePair:
    def __init__(self, pair_id, img1_path, img2_path, store=None, session=None):
        self.store = store # name of store: i.e. store_eb36deb2-bcab-4f89-8536-2dd6e0a0d7aa
        self.session = session # name of session: i.e.session_d026e74d-68dd-4cea-9089-48682fdaa5b9

        self.pair_id = pair_id
        self.image1 = AnnotatableImage(img1_path, image_id=1)
        self.image2 = AnnotatableImage(img2_path, image_id=2)

        self.image_id = 1 if self.image1 else 2
        self.pair_annotation = None

    def update_pair_annotation(self, pair_annotation):
        self.pair_annotation = pair_annotation


class PairLoader:
    def __init__(self, src):
        self.src = Path(src)
        self.images = sorted(self.src.glob("*.jpeg"), key=lambda f: int(f.name.split("-")[0]))
        assert len(self.images) > 0, f"No images found at {src}"

        self.image_pairs = [
            ImagePair(idx, self.images[idx], self.images[idx + 1]) # self.images[idx] returns path for ImagePair
            for idx in range(len(self.images) - 1)
        ]
        self.current_index = 0

    def __getitem__(self, index):
        return self.image_pairs[index]

    def __iter__(self):
        return iter(self.image_pairs)

    def __len__(self):
        return len(self.image_pairs)

    def current_pair(self):
        return self.image_pairs[self.current_index]

    def next_pair(self):
        if self.current_index < len(self.image_pairs) - 1:
            self.current_index += 1

            return self.image_pairs[self.current_index]

    def prev_pair(self):
        if self.current_index > 0:
            self.current_index -= 1
            return self.image_pairs[self.current_index]
    
    def has_next(self):
        return self.current_index < len(self.image_pairs) - 1

    def has_prev(self):
        return self.current_index > 0

    def last_pair(self):
        self.current_index = len(self.image_pairs) - 1