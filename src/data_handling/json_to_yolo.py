import json
import shutil
from pathlib import Path
from itertools import chain


class YoloPaths:
    def __init__(self, split_dir):
        self._split_dir = split_dir
        
    @property
    def images1(self):
        return self._split_dir / "images"
    
    @property
    def images2(self):
        return self._split_dir / "images2"
    
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
    

def export_session(annotation_file, index, yolo_splitted_paths: YoloPathsSplit):
    # Load your annotations
    with open(annotation_file) as f:
        annotations = json.load(f)

    print(f"Loaded {len(annotations)} pairs.")

    # === EXPORT LOOP ===
    for pair_id, pair_data in annotations.items():
        if int(pair_id) % 10 == 0:
            yolo_paths = yolo_splitted_paths.val
        else:
            yolo_paths = yolo_splitted_paths.train
            
        im1_path = Path(pair_data["im1_path"])
        im2_path = Path(pair_data["im2_path"])
        index_string = str(index).zfill(7)

        im1_target = yolo_paths.images1 / f"{index_string}{im1_path.suffix}"
        im2_target = yolo_paths.images2 / f"{index_string}{im2_path.suffix}"

        shutil.copy(im1_path, im1_target)
        shutil.copy(im2_path, im2_target)

        # === Save YOLO labels ONLY for images1 ===
        boxes = pair_data.get("boxes1", [])
        image_size = pair_data.get("image1_size")
        img_w, img_h = image_size
        img_w, img_h = float(img_w), float(img_h)

        label_path = yolo_paths.labels / f"{index_string}.txt"

        with open(label_path, "w") as lf:
            if boxes:
                for box in boxes:
                    x1, y1, x2, y2 = float(box['x1']), float(box['y1']), float(box['x2']), float(box['y2'])
                    cx = ((x1 + x2) / 2) / img_w
                    cy = ((y1 + y2) / 2) / img_h
                    w = (x2 - x1) / img_w
                    h = (y2 - y1) / img_h

                    lf.write(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")
            else:
                # Write empty file for no boxes
                lf.write("")

        print(f"✅ Saved Pair {index_string}:")
        print(f"   Image1: {im1_target}")
        print(f"   Image2: {im2_target}")
        print(f"   Labels: {label_path}")
        index += 1

    print("\n🎉 Export finished successfully!")
    return index


if __name__ == "__main__":
    
    # === CONFIG ===
    yolo_splitted_paths = YoloPathsSplit(Path("/media/fast/dataset/bildunterschied/real_data/v2_tiny"))
    # IMAGES1_DIR = EXPORT_DIR / "images"
    # IMAGES2_DIR = EXPORT_DIR / "images2"
    # LABELS_DIR = EXPORT_DIR / "labels"

    # Create output folders
    for yolo_paths in [yolo_splitted_paths.val, yolo_splitted_paths.train]:
        for p in [yolo_paths.images1, yolo_paths.images2, yolo_paths.labels]:
            p.mkdir(parents=True, exist_ok=True)

    #  = SESSION_PATH / "converted_data.json"
    # SRC_DATA_PATH = Path("/media/fast/dataset/bildunterschied/test_mini/new_label_tool/one")
    dataset_small_set = Path("/media/fast/dataset/bildunterschied/test_mini/small_set").glob("**/converted_data.json")
    dataset_small_set2 = Path("/media/fast/dataset/bildunterschied/test_mini/small_set2").glob("**/converted_data.json")
    dataset_small_set3 = Path("/media/fast/dataset/bildunterschied/test_mini/small_set3").glob("**/converted_data.json")
    dataset_one = Path("/media/fast/dataset/bildunterschied/test_mini/new_label_tool/one").glob("**/annotations.json")
    
    
    annotation_files = chain(
        dataset_small_set,
        dataset_one,
        dataset_small_set2,
        dataset_small_set3,
        # folder_path.glob("**/*.json")
    )
    index = 0
    for f in annotation_files:
        print(f)
        index = export_session(f, index, yolo_splitted_paths)
        
    from yolo_config import generate_dataset_config
    
    class_names = [
        "product"
    ]
    
    generate_dataset_config(
        class_names=class_names,
        train_path=str(yolo_splitted_paths.train.images1),
        val_path=str(yolo_splitted_paths.val.images1),
        output_file=yolo_splitted_paths.yaml
    )