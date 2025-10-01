import json
import tkinter as tk
from PIL import Image
from app_annotation import ImagePairViewer, ImageAnnotation
import config
import image_annotation

def test_navigation_autosave(tmp_path):
    # Make sure dataset root is inside tmp_path
    config.DATASET_DIR = str(tmp_path)
    image_annotation.DATASET_DIR = str(tmp_path)

    # Create fake dataset with 4 images → 2 pairs
    store = tmp_path / "store_1" / "session_1"
    store.mkdir(parents=True)
    for i in range(4):
        img = Image.new("RGB", (10, 10), color="green")
        img.save(store / f"{i}-000000.jpeg", format="JPEG")

    # Launch viewer
    root = tk.Tk()
    root.withdraw()
    try:
        viewer = ImagePairViewer(root, tmp_path)
        viewer.reset(store)

        # Add a box to first pair
        viewer.image1.boxes = [{
            "x1": 1, "y1": 1, "x2": 5, "y2": 5,
            "annotation_type": ImageAnnotation.Classes.ANNOTATION
        }]

        # Navigate to next pair → should trigger autosave for pair 0
        viewer.right()

        ann_file = store / "annotations.json"
        data = json.loads(ann_file.read_text())

        # Check that pair 0 was saved even though we didn't call _maybe_save
        assert "0" in data
        assert data["0"]["pair_state"] == ImageAnnotation.Classes.ANNOTATED
        assert len(data["0"]["boxes"]) == 1

        # Add a box to second pair
        viewer.image1.boxes = [{
            "x1": 10, "y1": 10, "x2": 20, "y2": 20,
            "annotation_type": ImageAnnotation.Classes.ANNOTATION
        }]

        # Navigate left → should autosave pair 1
        viewer.left()

        data = json.loads(ann_file.read_text())
        assert "1" in data
        assert data["1"]["pair_state"] == ImageAnnotation.Classes.ANNOTATED
        assert len(data["1"]["boxes"]) == 1

    finally:
        root.destroy()
