import json
import pytest
import uuid
from pathlib import Path
from PIL import Image, ImageTk
import tkinter as tk

from logic_loader import PairLoader
from logic_saver import AnnotationSaver
from ui_annotation import BoxHandler


@pytest.fixture
def setup_pair(tmp_path):
    """Create a dummy dataset with 2 JPEGs (1 pair) + init saver and handler."""
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    for i in range(2):
        img = Image.new("RGB", (50, 60), color=(i*100, 0, 0))
        img.save(dataset / f"{i}-test.jpeg")

    loader = PairLoader(dataset)
    saver = AnnotationSaver(tmp_path)

    # Tk root (needed for Canvas to exist)
    root = tk.Tk()
    canvas = tk.Canvas(root, width=50, height=60)
    canvas.pack()

    pair = loader.current_pair()
    handler = BoxHandler(pair, saver)

    return root, canvas, pair, saver, handler


def test_delete_box_removes_from_json(setup_pair):
    root, canvas, pair, saver, handler = setup_pair

    # --- create a fake box ---
    box_id = str(uuid.uuid4())
    box = {
        "x1": 5, "y1": 5, "x2": 20, "y2": 20,
        "annotation_type": "item_removed",
        "pair_id": box_id,
    }
    pair.image1.boxes.append(box)
    saver.save_box(pair, box)

    pid = str(pair.pair_id)

    # --- sanity check before delete ---
    assert any(b["pair_id"] == box_id for b in pair.image1.boxes)
    assert any(b["pair_id"] == box_id for b in saver.annotations[pid]["boxes"])
    before_mem = len(pair.image1.boxes)
    before_json = len(saver.annotations[pid]["boxes"])

    # --- simulate selection ---
    handler.selected_box_index = 0
    handler.selected_canvas = canvas
    handler.selected_image = pair.image1

    # --- delete the box ---
    handler.delete_box()

    # --- assert it was removed from memory ---
    after_mem = len(pair.image1.boxes)
    assert all(b["pair_id"] != box_id for b in pair.image1.boxes)
    assert after_mem == before_mem - 1

    # --- assert it was removed from JSON ---
    data = json.loads(saver.file.read_text())
    after_json = len(data[pid]["boxes"])
    assert all(b["pair_id"] != box_id for b in data[pid]["boxes"])
    assert after_json == before_json - 1

    # cleanup Tk
    root.destroy()
