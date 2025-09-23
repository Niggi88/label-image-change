# src/ui_logic_testing/test_walkthrough.py
import os, json, uuid, tkinter as tk, pytest
from pathlib import Path
from PIL import Image

from logic_loader import PairLoader
from logic_saver import AnnotationSaver
from ui_annotation import BoxHandler
from ui_annotation_displayer import AnnotationDisplayer


def _mk_jpeg(path: Path, size=(100, 100), color=(0, 0, 0)):
    img = Image.new("RGB", size, color=color)
    img.save(path, "JPEG")

@pytest.fixture
def setup_env(tmp_path):
    dataset_path = tmp_path / "dataset"
    saving_path  = tmp_path / "saves"
    dataset_path.mkdir()
    saving_path.mkdir()

    # ➜ need ≥3 images so next_pair() actually advances
    for i, col in enumerate([(200,0,0), (0,200,0), (0,0,200)]):
        _mk_jpeg(dataset_path / f"{i}-dummy.jpeg", (120, 90), color=col)

    loader = PairLoader(str(dataset_path))
    saver  = AnnotationSaver(str(saving_path))

    root = tk.Tk()
    root.withdraw()
    # canvases for left/right so we can test drawing too
    c_left  = tk.Canvas(root, width=400, height=300)
    c_right = tk.Canvas(root, width=400, height=300)
    c_left.pack(); c_right.pack()
    root.update_idletasks()  # 🔑 ensure proper canvas sizes

    handler = BoxHandler(loader.current_pair(), saver)  # ui=None ok for tests
    displayer = AnnotationDisplayer()

    return loader, saver, handler, displayer, c_left, c_right, saving_path, root

def _ann_json(saves_dir):
    with open(os.path.join(saves_dir, "annotations.json")) as f:
        return json.load(f)

class E:  # tiny event helper
    def __init__(self, x, y): self.x, self.y = x, y

def test_full_walkthrough(setup_env):
    loader, saver, handler, displayer, c_left, c_right, saves_dir, root = setup_env
    pair = loader.current_pair()
    img  = pair.image1
    pid  = str(pair.pair_id)

    # --- 1) Draw + Save a box -------------------------------------------------
    # Simulate a drag from (20,20) to (180,100) on a 400x300 canvas.
    handler.start_x, handler.start_y = 20, 20
    handler._drawing = True
    handler.end_box(E(180, 100), c_left, img)

    ann = _ann_json(saves_dir)
    assert pid in ann
    assert ann[pid]["pair_state"] == "annotated"
    assert len(ann[pid]["boxes"]) == 1
    box0 = ann[pid]["boxes"][0]
    pair_id = box0["pair_id"]

    # --- 2) Move the box (start_move → move_box → end_move) -------------------
    # Start inside the box region (roughly center of the drawn box)
    handler.start_move(E(80, 60), c_left, img)
    handler.move_box(E(100, 80), c_left)   # move by (+20, +20) in canvas space
    handler.end_move(E(100, 80))

    ann = _ann_json(saves_dir)
    moved = next(b for b in ann[pid]["boxes"] if b["pair_id"] == pair_id)
    assert (moved["x1"], moved["y1"]) != (box0["x1"], box0["y1"])  # changed coords

    # --- 3) Boxes are drawn on display_pair -----------------------------------
    # display_pair reads from JSON; it should draw at least one 'box' item.
    # (It draws on both canvases by design.)
    displayer.display_pair(c_left, c_right, pair, ann, max_w=800, max_h=600)
    # Tk canvas item count by tag
    assert len(c_left.find_withtag("box"))  > 0
    assert len(c_right.find_withtag("box")) > 0

    # --- 4) Delete the moved box ---------------------------------------------
    # Prepare selection context expected by handler.delete_box()
    img.boxes = [moved]   # mirror JSON into memory for the handler call
    handler.selected_image  = img
    handler.selected_canvas = c_left
    handler.selected_box_index = 0
    handler.delete_box()

    ann = _ann_json(saves_dir)
    assert ann[pid]["boxes"] == []

    # --- 5) Reset pair (state → unsure, boxes cleared) ------------------------
    saver.reset_pair(pair)
    ann = _ann_json(saves_dir)
    assert ann[pid]["pair_state"] == "no_annotation"
    assert ann[pid]["boxes"] == []

    # --- 6) Skipping: auto-mark as 'unsure' for unseen pairs ------------------
    loader.next_pair()  # there is a second pair because we created 3 images
    pair2 = loader.current_pair()
    assert not pair2.pair_annotation  # fresh visit
    saver.save_pair(pair2, "no_annotation")  # mimic UIElements.next_pair auto-save
    ann = _ann_json(saves_dir)
    assert ann[str(pair2.pair_id)]["pair_state"] == "no_annotation"

    root.destroy()
