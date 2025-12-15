import socket
import os
import json
import sys

CACHE = True
IMAGE_SIZE=2000
UI_SCALING=2.5
FONT_SCALING=2.5
SERVER_AVAILABLE = None
SERVER = "http://172.30.20.31:8010/"

# DATASET_NAME="complex"
DATASET_NAME="gemuese_netz_sub"

HOSTNAME = socket.gethostname()


# Basisverzeichnis bestimmen (funktioniert für Python + exe)
if getattr(sys, 'frozen', False):
    # Wenn als exe/.app läuft → Ordner der Binary
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Wenn im Python-Interpreter läuft → Ordner, wo config.py liegt
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

json_path = os.path.join(BASE_DIR, "user_config.json")

if os.path.exists(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    USERNAME = cfg.get("username", "unknown")
    DATASET_NAME = cfg.get("dataset_name", "default")
    DATASET_DIR = cfg.get("dataset_dir", "./dataset")
    SERVER = cfg.get("server", SERVER)
    LOCAL_LOG_DIR = cfg.get("local_log_dir", "./local_log_dir")
    SEGMENTATION_PATH = cfg.get("segmentation_path", "./segmented_boxes")
    print(f"[CONFIG] loaded from user_config.json: {USERNAME}, {DATASET_DIR}")
else:

    if HOSTNAME == "niggis-brain":
        DATASET_DIR = f"/media/fast/dataset/bildunterschied/labeling/{DATASET_NAME}"
        UI_SCALING=2.5
        FONT_SCALING=2.5
        DATASET_NAME="tmp"
        DATASET_DIR = f"/media/fast/dataset/bildunterschied/test_mini/new_label_tool/{DATASET_NAME}"
        USERNAME = "niklas"
        LOCAL_LOG_DIR = "/tmp"
    elif HOSTNAME == "niklas-XPS-15-9530":
        UI_SCALING=2.5
        FONT_SCALING=2.5
        DATASET_NAME="dev"
        DATASET_DIR = f"/home/niklas/dataset/bildunterschied/{DATASET_NAME}"
        USERNAME = "niklas"
    elif HOSTNAME == "sarah-XPS-15-9530":
        USERNAME = "sarah"
        DATASET_NAME = "sarah_20250801-20250816"
        # DATASET_DIR = f"/home/sarah/Documents/background_segmentation/{DATASET_NAME}"
        LOCAL_LOG_DIR = "/home/sarah/Documents/change_detection/label-image-chang/local_log_dir"
        SEGMENTATION_PATH = "/home/sarah/Documents/change_detection/local_paths/segmented_boxes"
        DATASET_DIR = f"/home/sarah/Documents/data/{DATASET_NAME}"

    elif HOSTNAME == "NB-ENDRES":
        USERNAME = "sarah_windoof"
        DATASET_NAME = "example_sessions"
        # DATASET_DIR = f"/home/sarah/Documents/background_segmentation/{DATASET_NAME}"
        DATASET_DIR = rf"C:\Users\sarah.endres\Documents\{DATASET_NAME}"
    elif HOSTNAME == "ml02":
            DATASET_DIR = f"/home/niklas.unverricht/dataset/dataset/snapshot_change_detection/{DATASET_NAME}"

        # _base_data_dir = Path("/home/niklas.unverricht/dataset/snapshot_change_detection")


    else:
        raise Exception("Unknown host", HOSTNAME)

