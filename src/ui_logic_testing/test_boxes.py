# test_boxes.py
import json
import pytest
from pathlib import Path
from PIL import Image
import uuid

from logic_loader import PairLoader, ImagePair, AnnotatableImage
from logic_saver import AnnotationSaver


@pytest.fixture
def setup_pair(tmp_path):
    # create dummy dataset with 2 JPEGs (1 pair)
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    for i in range(2):
        img = Image.new("RGB", (50, 60), color=(i*100, 0, 0))
        img.save(dataset / f"{i}-test.jpeg")

    loader = PairLoader(dataset)
    saver = AnnotationSaver(tmp_path)

    return loader, saver


def test_save_box_coordinates(setup_pair):
    loader, saver = setup_pair
    pair = loader.current_pair()

    # fake a box in image1 (item_removed)
    box_removed = {
        "x1": 5, "y1": 10, "x2": 20, "y2": 30,
        "pair_id": str(uuid.uuid4()),
        "annotation_type": "item_removed",
    }
    saver.save_box(pair, box_removed)

    # fake a box in image2 (item_added)
    box_added = {
        "x1": 0, "y1": 0, "x2": 49, "y2": 59,  # full image box
        "pair_id": str(uuid.uuid4()),
        "annotation_type": "item_added",
    }
    saver.save_box(pair, box_added)

    saved = saver.annotations[str(pair.pair_id)]
    boxes = saved["boxes"]

    # --- assertions ---
    assert len(boxes) == 2
    # coordinates must be within image sizes
    for b in boxes:
        assert 0 <= b["x1"] < b["x2"] <= pair.image1.img_size[0]
        assert 0 <= b["y1"] < b["y2"] <= pair.image1.img_size[1]
        assert b["annotation_type"] in ("item_removed", "item_added")

    # check JSON file
    annotations_file = saver.file
    data = json.loads(annotations_file.read_text())
    assert str(pair.pair_id) in data
    assert len(data[str(pair.pair_id)]["boxes"]) == 2
