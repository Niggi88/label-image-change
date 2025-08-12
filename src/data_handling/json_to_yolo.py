import sys
import json
import shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from itertools import chain
from config import DATASET_DIR

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
    

def export_session(annotation_file, index, yolo_splitted_paths: YoloPathsSplit, override_root=None):
    # Load your annotations
    with open(annotation_file) as f:
        annotations = json.load(f)

    print(f"Loaded {len(annotations)} pairs.")

    if override_root is None:
        root_path = Path(annotations["_meta"]["root"])
    else:
        root_path = Path(override_root)
    # === EXPORT LOOP ===
    for i, (pair_id, pair_data) in enumerate(annotations.items()):
        index += 1
        if pair_id == "_meta":
            continue  # skip metadata
        if i % 10 == 0:
            yolo_paths = yolo_splitted_paths.val
        else:
            yolo_paths = yolo_splitted_paths.train
            
        im1_path = root_path / pair_data["im1_path"]
        im2_path = root_path / pair_data["im2_path"]
        store, session, img1_str = pair_data["im1_path"].split("/")
        img1_str = img1_str.split(".")[0]
        store, session, img2_str = pair_data["im2_path"].split("/")
        img2_str = img2_str.split(".")[0]
        
        pair_guid = "__".join([store, session, img1_str, img2_str])
        # index_string = str(index).zfill(7)
        index_string = pair_guid
        
        im1_target = yolo_paths.images1 / f"{index_string}{im1_path.suffix}"
        im2_target = yolo_paths.images2 / f"{index_string}{im2_path.suffix}"

        # === Save YOLO labels ONLY for images1 ===
        pair_state = pair_data.get("pair_state", "no_annotation").lower()
        boxes = pair_data.get("boxes", [])
        img_w, img_h = map(float, pair_data["image2_size"])  # always use image2 size

        label_lines = []

        if pair_state == "nothing":
            label_lines = ["0"]
        elif pair_state == "chaos":
            label_lines = ["1"]
        elif pair_state == "annotated":
            for box in boxes:
                atype = box.get("annotation_type")
                if atype not in {"item_added", "item_removed"}:
                    raise Exception(f"invalid atype: {atype}")
                x1, y1, x2, y2 = float(box["x1"]), float(box["y1"]), float(box["x2"]), float(box["y2"])
                cx = ((x1 + x2) / 2) / img_w
                cy = ((y1 + y2) / 2) / img_h
                w = abs(x2 - x1) / img_w
                h = abs(y2 - y1) / img_h
                class_id = "2" if atype == "item_added" else "3"
                label_lines.append(f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
        elif pair_state == "no_annotation":
            continue
            #label_lines = ["0"]  # skip saving anything
        else:
            label_lines = ["0"]

        shutil.copy(im1_path, im1_target)
        shutil.copy(im2_path, im2_target)
        
        image_size = pair_data.get("image1_size")
        img_w, img_h = image_size
        img_w, img_h = float(img_w), float(img_h)

        label_path = yolo_paths.labels / f"{index_string}.txt"
        with open(label_path, "w") as lf:
            lf.write("\n".join(label_lines))

            print(f"✅ Saved Pair {index_string}:")
            print(f"   Image1: {im1_target}")
            print(f"   Image2: {im2_target}")
            print(f"   Labels: {label_path}")
        

    print("\n🎉 Export finished successfully!")

    return index


if __name__ == "__main__":
    
    # === CONFIG ===
    # yolo_splitted_paths = YoloPathsSplit(Path("/media/fast/dataset/bildunterschied/real_data/v2_tiny"))
    # yolo_splitted_paths = YoloPathsSplit(Path("/media/fast/dataset/bildunterschied/real_data/test_sarah"))
    yolo_splitted_paths = YoloPathsSplit(Path("/media/fast/dataset/bildunterschied/real_data/test_pair_id"))
    # IMAGES1_DIR = EXPORT_DIR / "images"
    # IMAGES2_DIR = EXPORT_DIR / "images2"
    # LABELS_DIR = EXPORT_DIR / "labels"

    # Create output folders
    for yolo_paths in [yolo_splitted_paths.val, yolo_splitted_paths.train]:
        for p in [yolo_paths.images1, yolo_paths.images2, yolo_paths.labels]:
            p.mkdir(parents=True, exist_ok=True)

    #  = SESSION_PATH / "converted_data.json"
    # SRC_DATA_PATH = Path("/media/fast/dataset/bildunterschied/test_mini/new_label_tool/one")
    # dataset_small_set = Path("/media/fast/dataset/bildunterschied/test_mini/small_set").glob("**/converted_data.json")
    # dataset_small_set2 = Path("/media/fast/dataset/bildunterschied/test_mini/small_set2").glob("**/converted_data.json")
    # dataset_small_set3 = Path("/media/fast/dataset/bildunterschied/test_mini/small_set3").glob("**/converted_data.json")
    # dataset_small_set4 = Path("/media/fast/dataset/bildunterschied/labeling/gemuese_netz_sub").glob("**/annotations.json")
    dataset_small_set4 = Path("/media/fast/dataset/bildunterschied/real_data/test_sarah/sarah").glob("*.json")

    # dataset_one = Path("/media/fast/dataset/bildunterschied/test_mini/new_label_tool/one").glob("**/annotations.json")
    # dataset_sarah = Path("/home/sarah/Documents/background_segmentation/small_relevant_sessions").glob("**/annotations.json")
    
    dataset_config = Path(DATASET_DIR)
    
    annotation_files = list(chain(
        # dataset_small_set,
        # dataset_small_set2,
        dataset_small_set4,
        # dataset_small_set2,
        # dataset_small_set3,
        # folder_path.glob("**/*.json")
        # dataset_config
    ))
    
    override_root = "/media/fast/dataset/bildunterschied/real_data/test_sarah/images"
    index = 0
    for f in annotation_files:
        # index = export_session(f, index, yolo_splitted_paths)
        index = export_session(f, index, yolo_splitted_paths, override_root=override_root)
    print(len(annotation_files))
    from yolo_config import generate_dataset_config
    
    class_names = [
        "nothing",  # 0
        "chaos",            # 1
        "annotated",       # 2
    ]
    
    generate_dataset_config(
        class_names=class_names,
        train_path=str(yolo_splitted_paths.train.images1),
        val_path=str(yolo_splitted_paths.val.images1),
        output_file=yolo_splitted_paths.yaml
    )