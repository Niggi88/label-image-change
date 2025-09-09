import requests
from pathlib import Path
import sys
import json

# Add parent directory of src/ to sys.path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATASET_DIR, USERNAME

BASE_URL = "http://172.30.20.31:8080"

ANNOTATION_URL = f"{BASE_URL}/upload_annotation"
IMAGE_UPLOAD_URL = f"{BASE_URL}/upload_image"

def find_annotation_files(dataset_dir):
    """Find all annotations.json files in session folders."""
    dataset_path = Path(dataset_dir)
    return list(dataset_path.glob("store_*/session_*/annotations.json"))

def build_session_id(annotation_path):
    """Extract session_id from its folder structure."""
    session_folder = annotation_path.parent
    store_name = session_folder.parent.name
    session_name = session_folder.name
    return f"{store_name}__{session_name}"

def upload_annotation(file_path, session_id):
    """Upload the annotation file to the server."""
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (f"{session_id}.json", f)}
            data = {
                'username': USERNAME,
                'session_id': session_id
            }
            response = requests.post(ANNOTATION_URL, files=files, data=data)
            if response.status_code == 200:
                print(f"✅ Uploaded {session_id}.json")
            else:
                print(f"❌ Failed to upload {session_id}.json — Status {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"💥 Error uploading {file_path}: {e}")

def upload_image(image_path: Path, relative_path: str):
    """Upload a single image with its relative path preserved."""
    try:
        with open(image_path, 'rb') as f:
            files = {'file': (image_path.name, f)}
            data = {
                'relative_path': relative_path
            }
            response = requests.post(IMAGE_UPLOAD_URL, files=files, data=data)
            if response.status_code == 200:
                print(f"📸 Uploaded image: {relative_path}")
            else:
                print(f"❌ Failed to upload image {relative_path} — Status {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"💥 Error uploading image {image_path}: {e}")

def upload_images_from_annotation(annotation_path: Path):
    """Parse annotation file and upload referenced images."""
    try:
        with open(annotation_path) as f:
            data = json.load(f)
    except Exception as e:
        print(f"💥 Failed to read {annotation_path}: {e}")
        return

    # root = Path(data["_meta"]["root"])
    if data["_meta"].get("root") is not None:
        root = Path(data["_meta"]["root"])
        # do work
    else:
        print("skipped, no root")
        return

    for key, value in data.items():
        if key == "_meta":
            continue
        if root is None:
            return
        else: 
            for img_key in ["im1_path", "im2_path"]:
                rel_path = value[img_key]
                img_full_path = root / rel_path
                if img_full_path.exists():
                    upload_image(img_full_path, rel_path)
                else:
                    print(f"⚠️ Missing image: {img_full_path}")

def main():
    annotation_files = find_annotation_files(DATASET_DIR)
    if not annotation_files:
        print("⚠️ No annotations.json files found.")
        return

    print(f"Found {len(annotation_files)} annotation files.\n")

    for annotation_path in annotation_files:
        try:
            with open(annotation_path) as f:
                data = json.load(f)
        except Exception as e:
            print(f"💥 Failed to read {annotation_path}: {e}")
            continue

        if not data.get("_meta", {}).get("completed", False) or not data.get("_meta", {}).get("usable", True):
            print(f"⏭️ Skipping {annotation_path} (not completed or unusable)")
            continue

        session_id = build_session_id(annotation_path)

        # Upload annotation file
        upload_annotation(annotation_path, session_id)

        # Upload all referenced images from that annotation
        upload_images_from_annotation(annotation_path)

if __name__ == "__main__":
    main()
