# label-image-change

# how to use
1. start api on server:
- navigate to ~/sarah/sam_api
- activate sam_venv: source sam_venv/bin/activate

- navigate to ~/sarah/sam_api/src
- run python3 main.py -> starting:

2. run app.py
- canvas will open, ready to annotate
- json is saved in same folder as regarding session

3. parse json to yolo format
- run json_to_yolo.py script, this will create 3 folders:
* images
*images2
*labels

A simple tool for annotating changes between consecutive images. Created to label changes in image sequences for scene change detection.

## Features

- View consecutive image pairs side by side
- Navigate through image sequence using arrow keys or on-screen controls
- Classify changes between images:
- Nothing changed 'n'
- Chaos 'c' / Reorder / (too much change to annotate)
- Annotate specific changes with bounding boxes 'a'

## Usage

1. Place images in a directory (numbered sequentially)
2. Start tool with directory path
3. Navigate through images with 's' -> left, 'f' -> right or spinner
4. Press 'a' to enter annotation mode and to leave annotation mode
5. Draw boxes around changes
    - for added product on right image
    - for removed product on left images 
    - so always on the image where the product actually is
    - multiple boxes are possible
6. chaos short cut 'c'
    - if there is a hand blocking view to any relevant part of the image
    - if there is too much movement in the cart
    - if the customer moves items in around in the cart
7. nothing happened 'n'
    - if nothing happened
    - no products added or removed
    - no products moved around


## UML
![uml](image.png)

## Current Issues

- State management between annotation modes needs improvement
- Box persistence issues when navigating between images
- Annotation mode doesn't properly reset when changing images

## TODO

- alle boxen anzeigen
- alle boxen sicher persistieren auch bei zurück clicken
- Add clear boxes button
- Support processing multiple sessions/directories
- Visual indication when multiple boxes are drawn on same image
- Replace boxes with segmentation

### Maybe Later

- Make boxes editable (move/resize)
- Delete individual boxes
- Different colors for different types of changes
