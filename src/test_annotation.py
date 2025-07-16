import json
from pathlib import Path
import base64
from PIL import Image
import io

# 🔗 1) Update this path to your actual annotations.json!
ANNOTATIONS_PATH = Path("/home/sarah/Documents/background_segmentation/relevant_sessions/store_8dbefa14-0515-47d3-aa69-470d9ee271b3/session_a002753b-b641-4c7e-a311-e28217de4012/annotations.json")

import json
from pathlib import Path
from PIL import Image, ImageDraw

# ==== CONFIG ====
# Passe diesen Pfad an dein Session-Verzeichnis an:
SESSION_PATH = Path("/home/sarah/Documents/background_segmentation/relevant_sessions/store_8dbefa14-0515-47d3-aa69-470d9ee271b3/session_a002753b-b641-4c7e-a311-e28217de4012")
ANNOTATIONS_FILE = SESSION_PATH / "annotations.json"
OUTPUT_DIR = SESSION_PATH / "test_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# ==== Lese die JSON ====
with open(ANNOTATIONS_FILE, 'r') as f:
    annotations = json.load(f)

print(f"Loaded {len(annotations)} annotations.")

# ==== Hilfsfunktion zum Zeichnen ====
def draw_boxes(image_path, boxes, out_name):
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    for box in boxes:
        x1, y1 = box['x1'], box['y1']
        x2, y2 = box['x2'], box['y2']
        color = "red" if box['annotation_type'] == "red" else "green"
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

    img.save(OUTPUT_DIR / out_name)
    print(f"Saved: {OUTPUT_DIR / out_name}")

# ==== Über alle Pairs iterieren ====
for pair_id, data in annotations.items():
    im1_path = Path(data['im1_path'])
    im2_path = Path(data['im2_path'])
    boxes1 = data['boxes1']
    boxes2 = data['boxes2']

    print(f"\nPair {pair_id}:")
    print(f" - {im1_path} -> {len(boxes1)} boxes")
    print(f" - {im2_path} -> {len(boxes2)} boxes")

    # Male und speichere
    draw_boxes(im1_path, boxes1, f"pair_{pair_id}_im1.jpg")
    draw_boxes(im2_path, boxes2, f"pair_{pair_id}_im2.jpg")
