# label-image-change


A simple tool for annotating changes between consecutive images. Created to label changes in image sequences for scene change detection.

## Features
- View consecutive image pairs side by side
- Navigate through image sequence using arrow keys or on-screen controls
- Classify changes between images:
 - Nothing changed
 - Reorder (too much change to annotate)
 - Annotate specific changes with bounding boxes

## Usage
1. Place images in a directory (numbered sequentially)
2. Start tool with directory path
3. Navigate through images with arrow keys or spinner
4. Press 'a' to enter annotation mode
5. Draw boxes around changes
6. Use arrow keys to move to next/previous image pair

## Current Issues
- State management between annotation modes needs improvement
- Box persistence issues when navigating between images
- Annotation mode doesn't properly reset when changing images

## TODO
- Add clear boxes button 
- Support processing multiple sessions/directories
- Visual indication when multiple boxes are drawn on same image 

### Maybe Later
- Make boxes editable (move/resize)
- Delete individual boxes
- Different colors for different types of changes
