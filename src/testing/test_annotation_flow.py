import pytest
import json
import tkinter as tk
from pathlib import Path
from PIL import Image

from app_annotation import ImagePairViewer, ImageAnnotation
import config
import image_annotation

def test_annotation_flow(tmp_path):
    # Make sure dataset root is inside tmp_path
    image_annotation.DATASET_DIR = str(tmp_path)

    # Create fake dataset: store_1/session_1 with two valid jpeg files
    store = tmp_path / "store_1" / "session_1"
    store.mkdir(parents=True)
    for i in range(2):
        img = Image.new("RGB", (10, 10), color="red")
        img.save(store / f"{i}-000000.jpeg", format="JPEG")

    root = tk.Tk()
    root.withdraw()

    try:
        viewer = ImagePairViewer(root, tmp_path)
        viewer.reset(store)

        viewer.image1.boxes = [{
            "x1": 10, "y1": 10, "x2": 50, "y2": 50,
            "annotation_type": ImageAnnotation.Classes.ANNOTATION
        }]
        viewer._maybe_save(pair_state=ImageAnnotation.Classes.ANNOTATED)

        ann_file = store / "annotations.json"
        assert ann_file.exists()

        data = json.loads(ann_file.read_text())
        pair_entry = data["0"]
        assert pair_entry["pair_state"] == ImageAnnotation.Classes.ANNOTATED
        assert len(pair_entry["boxes"]) == 1
    finally:
        root.destroy()


def test_imageannotation_save_and_load(tmp_path):
    # Patch DATASET_DIR for relative path
    config.DATASET_DIR = str(tmp_path)

    ann = ImageAnnotation(base_path=tmp_path, total_pairs=1)

    # Fake image objects
    class FakeImage:
        def __init__(self):
            self.controller = type("c", (), {"current_index": 0})()
            self.image_path = tmp_path / "0.jpeg"
            img = Image.new("RGB", (10, 10), color="blue")
            img.save(self.image_path, format="JPEG")
            self.image_size = (10, 10)
        def get_boxes(self):
            return [{"x1":1,"y1":2,"x2":3,"y2":4,"annotation_type":"item_added"}]

    im1, im2 = FakeImage(), FakeImage()
    ann.save_pair_annotation(im1, im2, pair_state="annotated")

    data = json.loads((tmp_path/"annotations.json").read_text())
    assert "0" in data
    assert data["0"]["pair_state"] == "annotated"
    assert len(data["0"]["boxes"]) == 2
