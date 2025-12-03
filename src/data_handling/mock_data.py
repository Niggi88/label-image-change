import numpy as np
# import cv2
from typing import List
from PIL import Image
import os
from collections import Counter
from enum import Enum, auto
import cv2

if __name__ == '__main__':
    import sys
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[1]  # Repo-Root
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from data_handling import data_config as config


class DatasetSplit(Enum):
    TRAIN = auto()
    VAL = auto()
    TEST = auto()

class MockDataset():
    
    def __init__(self, size=config.IMAGE_SIZE):
        self.size = size
        
    def __len__(self):
        return len(self.image_files)
    
    def random_class(self):
        rand = np.random.uniform()
        if rand < 0.33:
            cl = 0
        elif rand < 0.66:
            cl = 1
        else:
            cl = 2
        return cl

    def random_box(self):
        """Generate random box with Gaussian distribution, ensuring it stays within [0,1] bounds"""
        # Generate width and height with normal distribution
        # abs() ensures positive values, clip ensures reasonable range
        w = np.clip(abs(np.random.randn() * 0.1 + 0.15), 0.05, 0.8)  # mean~0.15, std~0.1
        h = np.clip(abs(np.random.randn() * 0.1 + 0.15), 0.05, 0.8)
        
        # Generate center with normal distribution (centered at 0.5)
        # But must ensure box stays within bounds
        x_center = np.random.randn() * 0.15 + 0.5  # centered at middle
        y_center = np.random.randn() * 0.15 + 0.5
        
        # Clip to ensure box stays inside image
        x_center = np.clip(x_center, w/2, 1 - w/2)
        y_center = np.clip(y_center, h/2, 1 - h/2)
        
        return x_center, y_center, w, h
    
    def xywh2xyxy(self, box):
        x, y, w, h = box
        x1 = x - w/2
        x2 = x + w/2
        y1 = y - h/2
        y2 = y + h/2
        return [x1, y1, x2, y2]

    def pct2px(self, box, width, height):
        x1, y1, x2, y2 = box
        return [int(x1*width), int(y1*height), int(x2*width), int(y2*height)]
    
    def get_item(self):
        # Load images

        width = self.size
        height = np.random.randint(int(0.5*width), width)
        img1 = np.zeros(shape=(height, width, 3))
        img2 = img1.copy()
        cl = self.random_class()

        label = np.zeros(7)

        if cl == 2:
            box = self.random_box()
            boxes = [box]
            x1, y1, x2, y2 = self.pct2px(self.xywh2xyxy(box), width, height)
            print(x1, y1, x2, y2)
            img2[x1:x2, y1:y2, :] = 255.
            label[3:] = box[:]
        else:
            boxes = []
            if cl == 1:
                img2[:,:, 1] = 255. 

        img1 = img1.astype(np.uint8)
        img2 = img2.astype(np.uint8)

        return img1, img2, label

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
    
    
class YoloPathsSplit:
    def __init__(self, split_dir):
        self._split_dir = split_dir
        self.val = YoloPaths(split_dir / "val")
        self.train = YoloPaths(split_dir / "train")
    
    @property
    def yaml(self):
        return self._split_dir / "dataset.yaml"
    

def export_session(dataset: MockDataset, yolo_splitted_paths: YoloPathsSplit, n_samples=20):
    # Load your annotations



    for index in range(n_samples):
        img1, img2, label = dataset.get_item()
        pair_guid = f"{str(index).zfill(7)}"

        if index % 10 == 0:
            yolo_paths = yolo_splitted_paths.val
        else:
            yolo_paths = yolo_splitted_paths.train
            
        
        # index_string = str(index).zfill(7)
        index_string = pair_guid
        
        im1_target = yolo_paths.images1 / f"{index_string}.jpeg"
        im2_target = yolo_paths.images2 / f"{index_string}.jpeg"

        # === Save YOLO labels ONLY for images1 ===

        label_lines = [str(label)]

        cv2.imwrite(im1_target, img1)
        cv2.imwrite(im2_target, img2)

        # image_size = pair_data.get("image1_size")
        # img_w, img_h = image_size
        # img_w, img_h = float(img_w), float(img_h)

        label_path = yolo_paths.labels / f"{index_string}.txt"
        with open(label_path, "w") as lf:
            lf.write("\n".join(label_lines))

            print(f"✅ Saved Pair {index_string}:")
            print(f"   Image1: {im1_target}")
            print(f"   Image2: {im2_target}")
            print(f"   Labels: {label_path}")
        

    print("\n🎉 Export finished successfully!")

    return index


# Simple test
if __name__ == '__main__':
    dataset_name = "mock_tiny"

    yolo_splitted_paths = YoloPathsSplit(config.out_datasets_dir)
    # Create output folders
    for yolo_paths in [yolo_splitted_paths.val, yolo_splitted_paths.train]:
        for p in [yolo_paths.images1, yolo_paths.images2, yolo_paths.labels]:
            p.mkdir(parents=True, exist_ok=True)

    # location = Path("/home/niklas/dataset/snapshot_change_detection/datasets/datasets")
    dataset = MockDataset()
    
    export_session(dataset, yolo_splitted_paths, n_samples=20_000)
    