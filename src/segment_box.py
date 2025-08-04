import numpy as np
import os
# import torch
# import matplotlib.pyplot as plt
import cv2
import sys
import requests
import base64
import numpy as np
import cv2
from PIL import Image, ImageDraw
import io
sys.path.append("..")



def show_mask(mask, ax, random_color=False):
    if random_color:
        color = np.concatenate([np.random.random(3), np.array([0.6])], axis=0)
    else:
        color = np.array([30/255, 144/255, 255/255, 0.6])
    h, w = mask.shape[-2:]
    mask_image = mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
    ax.imshow(mask_image)


def show_points(coords, labels, ax, marker_size=375):
    pos_points = coords[labels==1]
    neg_points = coords[labels==0]
    ax.scatter(pos_points[:, 0], pos_points[:, 1], color='green', marker='*', s=marker_size, edgecolor='white', linewidth=1.25)
    ax.scatter(neg_points[:, 0], neg_points[:, 1], color='red', marker='*', s=marker_size, edgecolor='white', linewidth=1.25)   


def show_box(box, ax):
    x0, y0 = box[0], box[1]
    w, h = box[2] - box[0], box[3] - box[1]
    ax.add_patch(plt.Rectangle((x0, y0), w, h, edgecolor='green', facecolor=(0,0,0,0), lw=2))    


def create_checkerboard(size=(512, 512), block_size=32):
    """Creates a checkerboard pattern."""
    rows, cols = size
    pattern = np.zeros((rows, cols), dtype=np.uint8)
    for i in range(0, rows, block_size * 2):
        for j in range(0, cols, block_size * 2):
            pattern[i:i+block_size, j:j+block_size] = 255
            pattern[i+block_size:i+block_size*2, j+block_size:j+block_size*2] = 255
    return pattern


def blend_with_checkerboard(img):
    """Blends a transparent image with a checkerboard pattern."""
    rows, cols, _ = img.shape
    checkerboard = create_checkerboard((rows, cols))
    blended = cv2.merge((checkerboard, checkerboard, checkerboard, np.ones((rows, cols), dtype=np.uint8) * 255))
    alpha = img[:, :, 3] / 255.0
    for c in range(3):  # For each channel R, G, B
        blended[:, :, c] = alpha * img[:, :, c] + (1 - alpha) * blended[:, :, c]
    return blended

def apply_mask_and_blur(image, mask, border_size=10, blur_radius=5):
    # Ensure that the mask is binary (0 or 255)
    _, mask_binary = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)

    # Create an empty result image with 4 channels (RGBA)
    result = np.zeros((image.shape[0], image.shape[1], 4), dtype=np.uint8)

    # Copy the image content to the result
    result[..., :3] = image

    # Set the alpha channel to the binary mask
    result[..., 3] = mask_binary
    
    # Find the bounding rectangle of the unmasked part
    contours, _ = cv2.findContours(mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    x, y, w, h = cv2.boundingRect(contours[0])

    # Add the border size to the bounding rectangle
    x = max(0, x - border_size)
    y = max(0, y - border_size)
    w = min(result.shape[1] - x, w + 2 * border_size)
    h = min(result.shape[0] - y, h + 2 * border_size)

    # Crop the result image using the adjusted bounding rectangle
    cropped_result = result[y:y+h, x:x+w]
    
    # Create a blurred version of the alpha channel
    blurred_alpha = cv2.GaussianBlur(cropped_result[..., 3], (blur_radius, blur_radius), 0)
    
    # Replace the original alpha channel with the blurred version
    cropped_result[..., 3] = blurred_alpha

    return cropped_result
#     

def get_model(device):
    # activate anaconda dataset
    from segment_anything import sam_model_registry, SamPredictor
    SAM_CHECKPOINT = "models/sam_vit_l_0b3195.pth"
    MODEL_TYPE = "vit_l"
    sam = sam_model_registry[MODEL_TYPE](checkpoint=SAM_CHECKPOINT)
    sam.to(device=device)
    predictor = SamPredictor(sam)
    return predictor

def get_model2():
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"💡 SAM2 uses device: {device}")

    model_cfg = "./configs/sam2.1/sam2.1_hiera_l.yaml"
    checkpoint = "/home/sarah/Documents/change_detection/label-image-change/src/models/sam2.1_hiera_large.pt"

    model = build_sam2(model_cfg, checkpoint, device)

    predictor = SAM2ImagePredictor(model)
    return predictor

    
import socket
from tkinter import messagebox

_server_reachable = None  # globaler Cache


def is_server_reachable(host, port, timeout=1):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def segment(image_np, box):
    global _server_reachable

    backend_host = "172.30.20.31"
    backend_port = 8000

    # Server-Reachability nur einmal prüfen
    if _server_reachable is None:
        _server_reachable = is_server_reachable(backend_host, backend_port)
        if not _server_reachable:
            messagebox.showwarning("Server nicht erreichbar", "Das Backend ist aktuell nicht erreichbar.\nEs wird eine Dummy-Maske verwendet.")

    if not _server_reachable:
        return None, {"success": False, "message": "No mask (server not reachable)"}

    # Wenn Server erreichbar, normal weitermachen
    tmp_path = "/tmp/tmp_image.jpg"
    cv2.imwrite(tmp_path, cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR))

    files = {
        "file": open(tmp_path, "rb")
    }
    data = {
        "x1": int(box[0]),
        "y1": int(box[1]),
        "x2": int(box[2]),
        "y2": int(box[3]),
    }

    try:
        response = requests.post(
            f"http://{backend_host}:{backend_port}/segment/box",
            files=files,
            data=data,
            timeout=5
        )
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            mask_data = base64.b64decode(result["mask"])
            mask_pil = Image.open(io.BytesIO(mask_data)).convert("RGBA")
            return mask_pil, result
        else:
            print("❌ Segmentierung fehlgeschlagen:", result)
            return create_dummy_mask(image_np, box), result

    except Exception as e:
        print(f"❌ Segmentierung fehlgeschlagen, benutze Dummy-Maske: {e}")
        return create_dummy_mask(image_np, box), {"success": False, "message": str(e)}


def create_dummy_mask(image_np, box):
    height, width = image_np.shape[:2]
    dummy_mask = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy_mask)
    draw.rectangle(
        [box[0], box[1], box[2], box[3]],
        fill=(255, 0, 0, 128)
    )
    return dummy_mask




def get_location(contours, image_width, image_height, only_largest=True):
    """
    Calculate the center and bounding box dimensions of contours in percentage of image dimensions.

    :param contours: List of contours.
    :param image_width: Width of the original image.
    :param image_height: Height of the original image.
    :param only_largest: If True, process only the largest contour. Otherwise, process all contours.
    :return: A list of dictionaries with the center and bounding box details of each contour.
    """
    # Sort contours by area
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    # List to store contour details
    contour_details = []

    # Process contours
    for i, contour in enumerate(contours):
        if only_largest and i > 0:
            break

        # Calculate the bounding box
        x, y, w, h = cv2.boundingRect(contour)

        # Calculate the gravity point (center)
        M = cv2.moments(contour)
        cX = int(M["m10"] / M["m00"]) if M["m00"] != 0 else 0
        cY = int(M["m01"] / M["m00"]) if M["m00"] != 0 else 0

        # Convert to percentage and adjust x, y to be the center
        details = {
            "x": ((cX / image_width)),
            "y": ((cY / image_height)),
            "w": (w / image_width),
            "h": (h / image_height)
        }

        contour_details.append(details)

    return contour_details


def main(in_directory, target_directory):
    images = os.listdir(in_directory)
    
    for image in images:
        idx = 0
        while True:  # Infinite loop to keep asking for user feedback until they decide to move on

            img = os.path.join(in_directory, image)
            # img = '3-dcc82d96-4d5e-4c54-be9c-e10220eab28af_top_0.jpeg'
            image_name = "_".join(image.split('.')[:-1]) + f"_{idx}"
            # trg = os.path.join(target_directory, image.split('.')[0]) + f"_{idx}"
            trg = os.path.join(target_directory, image_name) #+ f"_{idx}"
            cropped_result, details = segment(img)
            
            # Save the result
            output_path = f"{trg}.png"
            print("apply_mask_and_blur")
            print("write result to:", output_path)
            cv2.imshow('source', cv2.imread(img))
            cv2.imshow('cropped_result', blend_with_checkerboard(cropped_result))
            # cv2.moveWindow('source', 100, 100)
            # cv2.moveWindow('cropped_result', 400, 100)
            if not os.path.exists(trg):
                os.makedirs(os.path.dirname(trg), exist_ok=True)
            
            cv2.imwrite(output_path, cropped_result)
            
            with open(f"{trg}.txt", "w") as f:
                f.write(str(details[0]))

            print("Press 'r' to retry this iteration or any other key to continue to the next iteration.")
            key = cv2.waitKey(0) & 0xFF
            cv2.destroyAllWindows()

            # Check if 'r' key is pressed

            if key not in [ord('r'), ord('o')]:
                break

            if key == ord('o'):
                idx += 1


