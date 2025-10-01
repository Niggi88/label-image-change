# test_annotations.py
import json
import random
import pytest
from pathlib import Path
from PIL import Image

from ui_elements import UIElements
from logic_loader import PairLoader
from logic_saver import AnnotationSaver


@pytest.fixture
def setup_ui(tmp_path):
    # --- create dummy dataset with 3 small JPEGs (2 pairs) ---
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    for i in range(3):
        img = Image.new("RGB", (100, 100), color=(i*80, i*80, i*80))
        img.save(dataset / f"{i}-test.jpeg")

    # --- init loader & saver ---
    loader = PairLoader(dataset)
    saver = AnnotationSaver(tmp_path)

    # --- fake UIElements (no Tk) ---
    ui = UIElements.__new__(UIElements)  # bypass __init__ to avoid Tk
    ui.loader = loader
    ui.saver = saver

    return ui, saver, loader


def test_random_button_presses(setup_ui):
    ui, saver, loader = setup_ui
    valid_states = ["chaos", "nothing", "no_annotation", "annotated"]

    # simulate pressing random buttons for all pairs
    for i in range(len(loader)):
        state = random.choice(valid_states)
        loader.current_index = i
        ui.mark_state(state)

        pair = loader.current_pair()
        saved = saver.annotations[str(pair.pair_id)]

        # --- assertions ---
        assert saved["pair_state"] == state
        assert saved["im1_path"].endswith(".jpeg")
        assert saved["im2_path"].endswith(".jpeg")
        assert isinstance(saved["image1_size"], (list, tuple))
        assert isinstance(saved["image2_size"], (list, tuple))

    # --- check JSON file was written ---
    annotations_file = saver.file
    assert annotations_file.exists()
    content = json.loads(annotations_file.read_text())
    assert isinstance(content, dict)
    assert len(content) == len(loader)
