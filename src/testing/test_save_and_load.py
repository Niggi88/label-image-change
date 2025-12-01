import pytest
import json
import tkinter as tk
from pathlib import Path
from PIL import Image

from app_annotation import ImagePairViewer, ImageAnnotation
import config

def test_ten_boxes(tmp_path):
    # Make dataset root configurable
    config.DATASET_DIR = str(tmp_path)
    import image_annotation
    image_annotation.DATASET_DIR = str(tmp_path)

    # Create fake dataset
    store = tmp_path / "store_1" / "session_1"
    store.mkdir(parents=True)
    for i in range(2):
        img = Image.new("RGB", (10, 10), color="red")
        img.save(store / f"{i}-000000.jpeg", format="JPEG")

    # Launch viewer
    root = tk.Tk()
    root.withdraw()
    try:
        viewer = ImagePairViewer(root, tmp_path)
        viewer.reset(store)

        # Add 10 dummy boxes to image1
        boxes = []
        for i in range(10):
            boxes.append({
                "x1": i*10, "y1": i*10,
                "x2": i*10+40, "y2": i*10+40,
                "annotation_type": ImageAnnotation.Classes.ANNOTATION
            })
        viewer.image1.boxes = boxes

        # Save
        viewer._maybe_save(pair_state=ImageAnnotation.Classes.ANNOTATED)

        # Load JSON
        ann_file = store / "annotations.json"
        with open(ann_file, "r") as f:
            data = json.load(f)

        pair_entry = data["0"]
        assert pair_entry["pair_state"] == ImageAnnotation.Classes.ANNOTATED
        assert len(pair_entry["boxes"]) == 10
        assert pair_entry["boxes"][0]["x1"] == 0
        assert pair_entry["boxes"][9]["x1"] == 90
    finally:
        root.destroy()
