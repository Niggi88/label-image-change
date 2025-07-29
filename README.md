# label-image-change

A simple tool for annotating changes between consecutive images. Created to label changes in image sequences for scene change detection.

# How to use
# 1 (optional for generating masks): Start backend
* log into user sam
* cd backend/cart_SAMbackend
* source sam_venv/bin/activate
* open tmux window
*  run: python3  backend/cart_SAMbackend/src/main.py

# 2: Adjust config
*  set DATASET_DIR and DATASET_NAME (folder where all stores and sessions lie)
* optional: set scaling factors

# 3: Start annotating

* decide if you want to skip over already completed sessions or not

we have 4 classes:
        "nothing_changed",  # 0 (displayed as light blue)
        "chaos",            # 1 (displayed as yellow)
        "item_added",       # 2 (displayed as green box)
        "item_removed"      # 3 (disyplayed as red box)

## Options for annotating:
* nothing changed: when no item was added/removed, basically the content of the cart did not change
* chaos: when there is a lot going on, and its not clear whats going on (might be considered as unsure)
* annotate: lets you draw a box:
    - if an item was added (usually in the right image), draw a box around it
    - if and item was removed (when it is in the left image but not in the right image), draw a box about this item (left image)

* delete annotations:
    - delete selected: click on the button, then click on the box you want to remove, press button again, box and mirrored box disappear
    - clear all: deletes all annotations, leaving the state as "not_annotated", marking it as gray outline

* when no label fits to the image pair, you can skip, also defining that pair as "not annotated", marking it as gray outline


## Use keyboard shortcuts:

    → or f — next pair
    ← or s — previous pair
    a — annotate mode
    n — classify as "Nothing"
    c — classify as "Chaos"
    d — delete selected box
    x — clear all boxes

# 4: Parse annotations.json files into correct format

* for each session, a annotations.json file gets saved in the respective session folder (where this session's images lie)
* go to script: src/data_handling/json_to_yolo.py  and run it. since the location of the annotation files is accessed from config, it accessess the annotations from the respective folders



# Notes:
* dataset should have following saving strucutre: DATASET_DIR/DATASET_NAME/store_folder/session_folder/images.jpeg



## Features

- View consecutive image pairs side by side
- Navigate through image sequence using arrow keys or on-screen controls
- Classify changes between images:
- Nothing changed 'n'
- Chaos 'c' / Reorder / (too much change to annotate)
- Annotate specific changes with bounding boxes 'a'


