from pathlib import Path
from PIL import Image


class AnnotatableImage:
    def __init__(self, img_path, image_id):
        self.img_path = Path(img_path)
        self.img_size = Image.open(self.img_path).size if self.img_path.exists() else None
        self.boxes = []
        self.image_id = image_id 


class ImagePair:
    def __init__(self, pair_id, img1_path, img2_path):
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