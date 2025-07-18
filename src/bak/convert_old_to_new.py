import json
import os
from PIL import Image
from pathlib import Path

def get_image_size(image_path):
    """Get image dimensions from file path."""
    try:
        with Image.open(image_path) as img:
            return {"width": img.width, "height": img.height}
    except Exception as e:
        print(f"Error reading image {image_path}: {e}")
        return None

def convert_json_structure(input_file, output_file):
    """Convert JSON structure according to specifications."""
    
    # Load the JSON data
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    converted_data = {}
    
    for key, item in data.items():
        converted_item = {}
        
        # Convert im1 -> im1_path and im2 -> im2_path
        if "im1_path" in item:
            # Already converted
            converted_item["im1_path"] = item["im1_path"]
        elif "im1" in item:
            converted_item["im1_path"] = item["im1"]
            
        if "im2_path" in item:
            # Already converted
            converted_item["im2_path"] = item["im2_path"]
        elif "im2" in item:
            converted_item["im2_path"] = item["im2"]
        
        # Keep the type field
        if "type" in item:
            converted_item["type"] = item["type"]
        
        # Convert boxes structure
        if "boxes1" in item:
            # Already converted, keep the existing boxes1
            converted_item["boxes1"] = item["boxes1"]
        elif "boxes" in item and item["boxes"]:
            # Extract only the coordinate information, removing annotation_type
            boxes1 = []
            for box in item["boxes"]:
                box_coords = {
                    "x1": box["x1"],
                    "y1": box["y1"],
                    "x2": box["x2"],
                    "y2": box["y2"]
                }
                boxes1.append(box_coords)
            converted_item["boxes1"] = boxes1
        else:
            converted_item["boxes1"] = []
        
        # Get image sizes
        if "image1_size" in item:
            # Already have image1 size
            converted_item["image1_size"] = item["image1_size"]
        elif "im1_path" in converted_item:
            image1_size = get_image_size(converted_item["im1_path"])
            if image1_size:
                converted_item["image1_size"] = image1_size
        elif "im1" in item:
            image1_size = get_image_size(item["im1"])
            if image1_size:
                converted_item["image1_size"] = image1_size
        
        if "image2_size" in item:
            # Already have image2 size
            converted_item["image2_size"] = item["image2_size"]
        elif "im2_path" in converted_item:
            image2_size = get_image_size(converted_item["im2_path"])
            if image2_size:
                converted_item["image2_size"] = image2_size
        elif "im2" in item:
            image2_size = get_image_size(item["im2"])
            if image2_size:
                converted_item["image2_size"] = image2_size
        
        converted_data[key] = converted_item
    
    # Save the converted data
    with open(output_file, 'w') as f:
        json.dump(converted_data, f, indent=2)
    
    print(f"Conversion complete! Output saved to {output_file}")
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
        items_with_boxes = sum(1 for item in converted_data.values() if item.get("boxes1"))
        total_boxes = sum(len(item.get("boxes1", [])) for item in converted_data.values())
        
        print(f"\nSummary:")
        print(f"Total items processed: {total_items}")
        print(f"Items with boxes: {items_with_boxes}")
        print(f"Total boxes: {total_boxes}")
        
        # Show example of converted structure
        if converted_data:
            first_key = list(converted_data.keys())[0]
            print(f"\nExample converted item (key: {first_key}):")
            print(json.dumps(converted_data[first_key], indent=2))
        
    except Exception as e:
        print(f"Error processing file: {e}")

if __name__ == "__main__":
    # You can modify these file paths as needed
    
    BASE_DIR = Path("/media/fast/dataset/bildunterschied/test_mini/small_set/session_3b508f90-94c2-4909-916b-42d7bb361f48/")
    input_file = BASE_DIR / "annotations.json"
    output_file = BASE_DIR / "converted_data.json"
    
    process_json_file(str(input_file), str(output_file))