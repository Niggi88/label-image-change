class YoloPaths:
    def __init__(self, split_dir):
        self._split_dir = split_dir
        
    @property
    def images1(self):
        return self._split_dir / "images1" # links
    
    @property
    def images2(self):
        return self._split_dir / "images2" # rechts
    
    @property
    def labels(self):
        return self._split_dir / "labels"
    