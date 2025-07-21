import json
import shutil
from pathlib import Path
from itertools import chain


# === CONFIG ===
EXPORT_DIR = Path("/media/fast/dataset/bildunterschied/real_data/v2_tiny")
IMAGES1_DIR = EXPORT_DIR / "images"
IMAGES2_DIR = EXPORT_DIR / "images2"
LABELS_DIR = EXPORT_DIR / "labels"

# Create output folders
for p in [IMAGES1_DIR, IMAGES2_DIR, LABELS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# SESSION_PATH = Path(
#     "/home/sarah/Documents/background_segmentation/relevant_sessions/"
#     "store_8dbefa14-0515-47d3-aa69-470d9ee271b3/session_a002753b-b641-4c7e-a311-e28217de4012"
# )
# SESSION_PATH = Path(
#     "/media/fast/dataset/bildunterschied/test_mini/small_set/"
#     "session_3b508f90-94c2-4909-916b-42d7bb361f48"
# )



def export_session(annotation_file, index):
    # Load your annotations
    with open(annotation_file) as f:
        annotations = json.load(f)

    print(f"Loaded {len(annotations)} pairs.")

    # === EXPORT LOOP ===
    for pair_id, pair_data in annotations.items():
        im1_path = Path(pair_data["im1_path"])
        im2_path = Path(pair_data["im2_path"])
        index_string = str(index).zfill(7)

        im1_target = IMAGES1_DIR / f"{index_string}{im1_path.suffix}"
        im2_target = IMAGES2_DIR / f"{index_string}{im2_path.suffix}"

        shutil.copy(im1_path, im1_target)
        shutil.copy(im2_path, im2_target)

        # === Save YOLO labels ONLY for images1 ===
        boxes = pair_data.get("boxes1", [])
        image_size = pair_data.get("image1_size")
        img_w, img_h = image_size
        img_w, img_h = float(img_w), float(img_h)

        label_path = LABELS_DIR / f"{index_string}.txt"

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
        index = export_session(f, index)