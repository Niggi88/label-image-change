import json
import os
from PIL import Image
from pathlib import Path
from datetime import datetime
import uuid
from collections import Counter

def get_image_size(image_path):
    """Get image dimensions from file path."""
    try:
        with Image.open(image_path) as img:
            return [img.width, img.height]# {"width": img.width, "height": img.height}
    except Exception as e:
        print(f"Error reading image {image_path}: {e}")
        return None


def split_path(path):
    parts = path.split("/")
    specific = "/".join(parts[-3:])
    root = "/".join(parts[:-3])
    return root, specific

def convert_json_structure(input_file, output_file):
    """Convert JSON structure according to specifications."""
    box_types = {"green": "item_added", "red": "item_removed"}
    pair_states = {'annotation': "annotated", 'reorder': "chaos", 'nothing': "no_annotation", "annotation_xy": "annotated "}
    # Load the JSON data
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    root, specific = split_path(input_file)
    converted_data = {}
    _meta = {
        "completed": True,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
        "root": root,
    }
    converted_data["_meta"] = _meta
    
    for key, item in data.items():
        
        converted_item = {}
        pair_id = pair_id = str(uuid.uuid4())
        # Convert im1 -> im1_path and im2 -> im2_path
        if "im1_path" in item:
            # Already converted
            image_path = item["im1_path"]
        elif "im1" in item:
            image_path = item["im1"]
        converted_item["im1_path"] = image_path.replace(root, "")[1:]
            
        if "im2_path" in item:
            # Already converted
            converted_item["im2_path"] = item["im2_path"].replace(root, "")[1:]
        elif "im2" in item:
            converted_item["im2_path"] = item["im2"].replace(root, "")[1:]
        
        # Keep the type field
        if "type" in item:
            # converted_item["type"] = item["type"]
            converted_item["pair_state"] = pair_states[item["type"]]
        
        # Convert boxes structure
        if "boxes" in item:
            # Already converted, keep the existing boxes1
            boxes = item["boxes"]
            for box in boxes:
                box["annotation_type"] = box_types.get(box["annotation_type"])
                box["pair_id"] = pair_id
            converted_item["boxes"] = boxes
        elif "boxes" in item and item["boxes"]:
            # Extract only the coordinate information, removing annotation_type
            boxes = []
            for box in item["boxes"]:
                box_coords = {
                    "x1": box["x1"],
                    "y1": box["y1"],
                    "x2": box["x2"],
                    "y2": box["y2"],
                }
                boxes.append(box_coords)
            converted_item["boxes"] = boxes
            print(boxes)
        else:
            converted_item["boxes"] = []
        
        # Get image sizes
        if "image1_size" in item:
            # Already have image1 size
            converted_item["image1_size"] = item["image1_size"]
        elif "im1_path" in converted_item:
            image1_size = get_image_size(image_path)
            if image1_size:
                converted_item["image1_size"] = image1_size
        elif "im1" in item:
            image1_size = get_image_size(image_path)
            if image1_size:
                converted_item["image1_size"] = image1_size
        
        if "image2_size" in item:
            # Already have image2 size
            converted_item["image2_size"] = item["image2_size"]
        elif "im2_path" in converted_item:
            image2_size = get_image_size(image_path)
            if image2_size:
                converted_item["image2_size"] = image2_size
        elif "im2" in item:
            image2_size = get_image_size(image_path)
            if image2_size:
                converted_item["image2_size"] = image2_size
        
        converted_data[key] = converted_item
    
    # Save the converted data
    with open(output_file, 'w') as f:
        json.dump(converted_data, f, indent=2)
    
    print(f"Conversion complete! Output saved to {output_file}")
    # print(json.dumps(converted_data, indent=1))
    return converted_data

def process_json_file(input_file="paste.txt", output_file="converted_data.json"):
    """Main function to process the JSON file."""
    
    if not os.path.exists(input_file):
        print(f"Input file {input_file} not found!")
        return
    
    try:
        converted_data = convert_json_structure(input_file, output_file)
        
        # Print summary
        total_items = len(converted_data)
        items_with_boxes = sum(1 for item in converted_data.values() if item.get("boxes"))
        pair_states = [item["pair_state"] for key, item in converted_data.items() if key != "_meta"]
        state_counts = Counter(pair_states)
        total_boxes = sum(len(item.get("boxes", [])) for item in converted_data.values())
        
        print(f"\nSummary:")
        print(f"Total items processed: {total_items}")
        print(f"Items with boxes: {items_with_boxes}")
        print(f"Total boxes: {total_boxes}")
        print(f"{state_counts}")
        
        # Show example of converted structure
        if converted_data:
            first_key = list(converted_data.keys())[0]
            print(f"\nExample converted item (key: {first_key}):")
        
    except Exception as e:
        print(f"Error processing file: {e}")
        raise e
    return total_items

if __name__ == "__main__":
    # You can modify these file paths as needed
    
    BASE_DIR = Path("/media/fast/dataset/bildunterschied/test_mini/small_set")
    # BASE_DIR = Path("/media/fast/dataset/bildunterschied/test_mini/small_set2")
    # BASE_DIR = Path("/media/fast/dataset/bildunterschied/test_mini/small_set3") # everything seems to be empty ...
    
    input_files = BASE_DIR.glob("**/annotations.json")
    converted = 0
    for input_file in input_files: # list(input_files)[2:]:
        
        # input_file = BASE_DIR / "annotations.json"
        output_file = str(input_file).replace("annotations.json", "converted_data.json")
        
        # print("in:  ", str(input_file))
        # print("out: ", str(output_file))
        converted += process_json_file(str(input_file), output_file)
    print(f"converted {converted} images")