import json
import os
from pathlib import Path
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt

# Adjust path to your local annotations.json
ANNOTATION_DATA = Path("/home/sarah/Documents/background_segmentation/relevant_sessions").glob("**/annotations.json")


for file in ANNOTATION_DATA:
# Load annotation data
    with open(file, "r") as f:
        annotations = json.load(f)

    # Get root directory for absolute image paths
    root_dir = annotations["_meta"]["root"]

    # Iterate through all annotation entries
    for pair_idx, entry in annotations.items():
        if pair_idx == "_meta":
            continue

        im1_path = os.path.join(root_dir, entry["im1_path"])
        im2_path = os.path.join(root_dir, entry["im2_path"])

        try:
            image1 = Image.open(im1_path).convert("RGB")
            image2 = Image.open(im2_path).convert("RGB")
            image1.thumbnail((entry["image1_size"][0], entry["image1_size"][1]))
            image2.thumbnail((entry["image2_size"][0], entry["image2_size"][1]))
        except FileNotFoundError as e:
            print(f"[MISSING] {e}")
            continue

        # Draw boxes on image2
        if entry.get("boxes"):
            draw = ImageDraw.Draw(image2)
            for box in entry["boxes"]:
                draw.rectangle(
                    [(box["x1"], box["y1"]), (box["x2"], box["y2"])],
                    outline="lime",
                    width=3
                )
                draw.text((box["x1"], box["y1"] - 10), box["annotation_type"], fill="lime")

        # Display side by side
        fig, axs = plt.subplots(1, 2, figsize=(15, 6))
        axs[0].imshow(image1)
        axs[0].set_title(f"Image 1 (Pair {pair_idx} labeled as: {entry['pair_state']})")
        axs[1].imshow(image2)
        axs[1].set_title(f"Image 2")
        for ax in axs:
            ax.axis("off")

        plt.tight_layout()
        plt.show()

        # Wait for user input before continuing
        next_action = input("Press Enter to continue, q to quit: ")
        if next_action.lower() == "q":
            break
