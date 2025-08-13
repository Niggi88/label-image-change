import socket
from pathlib import Path

hostname = socket.gethostname()



print(hostname)


if hostname == "niklas-XPS-15-9530":
    _base_data_dir = Path("/home/niklas/dataset/bildunterschied/datasets")
    raw_data = _base_data_dir / "raw"
    override_root = raw_data / "images"
    _out_dataset_name = "test"
    out_datasets_dir = _base_data_dir / "datasets" / _out_dataset_name
    _src_data_name = "sarah"
    # "/media/fast/dataset/bildunterschied/real_data/test_sarah/images"