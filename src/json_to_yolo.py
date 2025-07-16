import json
import shutil
from pathlib import Path

# === CONFIG ===
EXPORT_DIR = Path("/home/sarah/Documents/change_detection/dataset")
IMAGES1_DIR = EXPORT_DIR / "images"
IMAGES2_DIR = EXPORT_DIR / "images2"
LABELS_DIR = EXPORT_DIR / "labels"

# Create output folders
for p in [IMAGES1_DIR, IMAGES2_DIR, LABELS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

SESSION_PATH = Path(
    "/home/sarah/Documents/background_segmentation/relevant_sessions/"
    "store_8dbefa14-0515-47d3-aa69-470d9ee271b3/session_a002753b-b641-4c7e-a311-e28217de4012"
)
ANNOTATIONS_FILE = SESSION_PATH / "annotations.json"

# Load your annotations
with open(ANNOTATIONS_FILE) as f:
    annotations = json.load(f)

print(f"Loaded {len(annotations)} pairs.")

# === EXPORT LOOP ===
for pair_id, pair_data in annotations.items():
    im1_path = Path(pair_data["im1_path"])
    im2_path = Path(pair_data["im2_path"])

    im1_target = IMAGES1_DIR / f"{pair_id}{im1_path.suffix}"
    im2_target = IMAGES2_DIR / f"{pair_id}{im2_path.suffix}"

    shutil.copy(im1_path, im1_target)
    shutil.copy(im2_path, im2_target)

    # === Save YOLO labels ONLY for images1 ===
    boxes = pair_data.get("boxes1", [])
    image_size = pair_data.get("image1_size")
    img_w, img_h = image_size

    label_path = LABELS_DIR / f"{pair_id}.txt"

    with open(label_path, "w") as lf:
        if boxes:
            for box in boxes:
                x1, y1, x2, y2 = box['x1'], box['y1'], box['x2'], box['y2']
                cx = ((x1 + x2) / 2) / img_w
                cy = ((y1 + y2) / 2) / img_h
                w = (x2 - x1) / img_w
                h = (y2 - y1) / img_h

                lf.write(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")
        else:
            # Write empty file for no boxes
            lf.write("")

    print(f"✅ Saved Pair {pair_id}:")
    print(f"   Image1: {im1_target}")
    print(f"   Image2: {im2_target}")
    print(f"   Labels: {label_path}")

print("\n🎉 Export finished successfully!")
