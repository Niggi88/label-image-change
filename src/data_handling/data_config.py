import socket
from pathlib import Path

hostname = socket.gethostname()


if hostname == "niklas-XPS-15-9530":
    _base_data_dir = Path("/home/niklas/dataset/snapshot_change_detection/datasets")
elif hostname == "ml02":
    _base_data_dir = Path("/home/niklas.unverricht/dataset/snapshot_change_detection")
elif hostname == "niggis-brain":
    _base_data_dir = Path("/media/fast/dataset/snapshot_change_detection")


CLASS_NAMES = [
    "nothing",
    "no_idea",
    "added",
]


_out_dataset_name = None # "large_xl-images_v3_0"
# _out_dataset_name = "testset_xl-images_v3_0"
src_data_names = None # ["santiago", "sarah", "almas"]
# src_data_names = ["niklas"]
IMAGE_SIZE = 832
raw_data = _base_data_dir / "change_data"
override_root = raw_data / "images"
out_datasets_dir = None # _base_data_dir / "real_data" / _out_dataset_name

NO_REMOVED = True