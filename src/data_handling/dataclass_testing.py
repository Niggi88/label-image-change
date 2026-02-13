from pathlib import Path
from annotation_verification import ImagePair


def test_folder(folder: Path):

    json_files = list(folder.glob("*.json"))

    print(f"Found {len(json_files)} json files")

    for json_file in json_files:
        try:
            pairs = ImagePair.read_json(json_file)
            print(pairs)
        except Exception as e:
            print("file: ", json_file.name)
            print(f"      {e}")


if __name__ == "__main__":

    folder = Path("/media/sarah/OS/snapshot_change_detection/data_validation/dataset/change_data/santiago") 

    test_folder(folder)