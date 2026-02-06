from yolo_utils.yolo_paths import YoloPaths


class YoloPathsSplit:
    def __init__(self, split_dir):
        self._split_dir = split_dir
        self.val = YoloPaths(split_dir / "val")
        self.train = YoloPaths(split_dir / "train")
    
    @property
    def yaml(self):
        return self._split_dir / "dataset.yaml"