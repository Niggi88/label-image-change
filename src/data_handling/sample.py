import cv2
import numpy as np
from pathlib import Path

from yolo_utils.yolo_paths_split import YoloPathsSplit


def rescale_box(box, orig_w, orig_h):
    x, y, w, h = box
    return int(x*orig_w), int(y*orig_h), int(w*orig_w), int(h*orig_h)


def xywh2xyxy(box):
    x, y, w, h = box
    x1, x2, y1, y2 = int(x - w / 2), int(x + w/2), int(y - h/2), int(y + h/2)
    return x1, y1, x2, y2
    
def visualize_prediction(img1_path, img2_path, class_name, box, probability):
    """
    Visualize change detection prediction with professional styling for presentations.
    
    Args:
        img1_path: Path to first image
        img2_path: Path to second image
        class_name: Predicted class name
        box: Bounding box in YOLO format [x_center, y_center, width, height] (normalized)
        probability: Confidence score (0-1)
        dataset: Dataset object for coordinate transformation
    
    Returns:
        concatenated: Professional visualization with labels and styling
    """
    # Load images
    img1 = cv2.imread(str(img1_path))
    img2 = cv2.imread(str(img2_path))
    
    # Ensure both images have the same size
    if img1.shape != img2.shape:
        img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
    
    orig_h, orig_w, _ = img1.shape
    
    # Professional color scheme
    COLOR_PRIMARY = (256, 0, 0) # config.classes.color.get(class_name, (0, 122, 255))
    COLOR_BG = (245, 245, 245)
    COLOR_TEXT = (40, 40, 40)
    COLOR_WHITE = (255, 255, 255) 
    FONT_SCALE = 1.2

    # Add subtle border/shadow effect
    border_size = 3
    img1 = cv2.copyMakeBorder(img1, border_size, border_size, border_size, border_size,
                               cv2.BORDER_CONSTANT, value=(200, 200, 200))
    img2 = cv2.copyMakeBorder(img2, border_size, border_size, border_size, border_size,
                               cv2.BORDER_CONSTANT, value=(200, 200, 200))
    
    # Draw bounding box with enhanced styling
    if class_name == "added" and box is not None:
        boxes = [xywh2xyxy(rescale_box(box)) for box in [box]]
        x1, y1, x2, y2 = boxes[0]
        
        # Semi-transparent overlay
        overlay = img2.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), COLOR_PRIMARY, -1)
        cv2.addWeighted(overlay, 0.15, img2, 0.85, 0, img2)
        
        # Main border
        cv2.rectangle(img2, (x1, y1), (x2, y2), COLOR_PRIMARY, 4)
        
        # Corner accents
        corner_len = min(30, (x2 - x1) // 4, (y2 - y1) // 4)
        for cx, cy, dx, dy in [(x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)]:
            cv2.line(img2, (cx, cy), (cx + dx * corner_len, cy), COLOR_WHITE, 3)
            cv2.line(img2, (cx, cy), (cx, cy + dy * corner_len), COLOR_WHITE, 3)
        
        # Reference box on first image (subtle)
        cv2.rectangle(img1, (x1, y1), (x2, y2), (180, 180, 180), 2, cv2.LINE_AA)
    
    # Professional label badge
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = FONT_SCALE * 1.2
    thickness = max(2, int(2.5 * FONT_SCALE))
    
    class_text = class_name.upper()
    prob_text = f"{int(probability * 100)}%"
    
    (class_w, class_h), _ = cv2.getTextSize(class_text, font, font_scale * 0.9, thickness)
    (prob_w, prob_h), baseline = cv2.getTextSize(prob_text, font, font_scale * 1.3, thickness + 1)
    
    padding_h, padding_v = int(20 * FONT_SCALE), int(15 * FONT_SCALE)
    badge_w = max(class_w, prob_w) + 2 * padding_h
    badge_h = class_h + prob_h + 3 * padding_v + baseline
    margin = int(20 * FONT_SCALE)
    
    # Gradient background
    for i in range(badge_h):
        alpha = 0.95 - (i / badge_h) * 0.1
        color = tuple(int(c * alpha + COLOR_BG[j] * (1 - alpha)) for j, c in enumerate(COLOR_PRIMARY))
        cv2.rectangle(img2, (margin, margin + i), (margin + badge_w, margin + i + 1), color, -1)
    
    cv2.rectangle(img2, (margin, margin), (margin + badge_w, margin + badge_h), COLOR_WHITE, 2, cv2.LINE_AA)
    
    # Text with shadow
    class_y = margin + padding_v + class_h
    prob_y = class_y + padding_v + prob_h
    text_x = margin + padding_h
    
    for text, y, scale, thick in [(class_text, class_y, 0.9, thickness), (prob_text, prob_y, 1.3, thickness + 1)]:
        cv2.putText(img2, text, (text_x + 2, y + 2), font, font_scale * scale, (0, 0, 0), thick, cv2.LINE_AA)
        cv2.putText(img2, text, (text_x, y), font, font_scale * scale, COLOR_WHITE, thick, cv2.LINE_AA)
    
    # Bottom labels
    label_scale = FONT_SCALE * 0.7
    label_thick = max(1, int(1.5 * FONT_SCALE))
    (lw, lh), lb = cv2.getTextSize("BEFORE", font, label_scale, label_thick)
    label_y = img1.shape[0] - margin
    
    for img, label in [(img1, "BEFORE"), (img2, "AFTER")]:
        lx = (img.shape[1] - lw) // 2
        cv2.rectangle(img, (lx - 10, label_y - lh - 8), (lx + lw + 10, label_y + lb + 8), COLOR_BG, -1)
        cv2.rectangle(img, (lx - 10, label_y - lh - 8), (lx + lw + 10, label_y + lb + 8), (180, 180, 180), 1, cv2.LINE_AA)
        cv2.putText(img, label, (lx, label_y), font, label_scale, COLOR_TEXT, label_thick, cv2.LINE_AA)
    
    # Separator and concatenate
    separator = np.ones((img1.shape[0], 8, 3), dtype=np.uint8) * 220
    result = np.hstack([img1, separator, img2])

    # separator = np.ones((img1.shape[0], 8, 3), dtype=np.uint8) * 220
    rig_h, orig_w = cv2.imread(str(img1_path)).shape[:2]
    expected_size = (orig_w * 2, orig_h)  # (width, height) für cv2.resize
    result = cv2.resize(result, expected_size)
    
    return result



def generate_sample(yolo_splitted_paths: YoloPathsSplit, number: int):
    sample_path: Path = yolo_splitted_paths.train.images1.parent.parent / "sample"
    sample_path.mkdir(exist_ok=True)
    print(sample_path)

    image_names_gen = yolo_splitted_paths.train.images1.glob("*")
    for i, img1_path in enumerate(image_names_gen):
        assert isinstance(img1_path, Path)
        # print(image_dir)
        image_name = img1_path.name
        img2_path = yolo_splitted_paths.train.images2 / image_name
        label_dir = yolo_splitted_paths.train.labels / image_name.replace(".jpeg", ".txt")
        out_dir = sample_path / image_name
        # image1 = cv2.imread(image_dir)
        # image2 = cv2.imread(image2_dir)
        # image = visualize_prediction(img1_path, img2_path, "class_name", box, probability)
        image = visualize_prediction(img1_path, img2_path, "class_name", [], 0.9)
        # image = np.concatenate([image1, image2], axis=1)
        cv2.imwrite(out_dir, image)

        print(image_name)
        if i > number:
            break
    print(sample_path)