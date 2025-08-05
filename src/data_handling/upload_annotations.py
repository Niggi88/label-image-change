import requests
from pathlib import Path
import sys
# Add parent directory of src/ to sys.path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATASET_DIR, USERNAME


SERVER_URL = "http://172.30.20.31:8080/upload_annotation"

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

def upload_file(file_path, session_id):
    """Upload the file to the server."""
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (f"{session_id}.json", f)}
            data = {
                'username': USERNAME,
                'session_id': session_id
            }
            response = requests.post(SERVER_URL, files=files, data=data)
            if response.status_code == 200:
                print(f"✅ Uploaded {session_id}.json")
            else:
                print(f"❌ Failed to upload {session_id}.json — Status {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"💥 Error uploading {file_path}: {e}")

def main():
    annotation_files = find_annotation_files(DATASET_DIR)
    if not annotation_files:
        print("⚠️ No annotations.json files found.")
        return

    print(f"Found {len(annotation_files)} annotation files.\n")

    for annotation_path in annotation_files:
        session_id = build_session_id(annotation_path)
        upload_file(annotation_path, session_id)

if __name__ == "__main__":
    main()
