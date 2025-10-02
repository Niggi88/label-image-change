import socket


CACHE = True
IMAGE_SIZE=2000
UI_SCALING=2.5
FONT_SCALING=2.5
SERVER_AVAILABLE = None
SERVER = "http://172.30.20.31:8010/"

# DATASET_NAME="complex"
DATASET_NAME="gemuese_netz_sub"

HOSTNAME = socket.gethostname()

if HOSTNAME == "niggis-brain":
    DATASET_DIR = f"/media/fast/dataset/bildunterschied/labeling/{DATASET_NAME}"
    UI_SCALING=2.5
    FONT_SCALING=2.5
    DATASET_NAME="tmp"
    DATASET_DIR = f"/media/fast/dataset/bildunterschied/test_mini/new_label_tool/{DATASET_NAME}"
    USERNAME = "niklas"
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
    LOCAL_LOG_DIR = f"/home/sarah/Documents/change_detection/label-image-chang/local_log_dir"
    SEGMENTATION_PATH = f"/home/sarah/Documents/change_detection/local_paths/segmented_boxes"
    DATASET_DIR = f"/home/sarah/Documents/data/{DATASET_NAME}"

elif HOSTNAME == "NB-ENDRES":
    USERNAME = "sarah_windoof"
    DATASET_NAME = "example_sessions"
    # DATASET_DIR = f"/home/sarah/Documents/background_segmentation/{DATASET_NAME}"
    DATASET_DIR = rf"C:\Users\sarah.endres\Documents\{DATASET_NAME}"

else:
    raise Exception("Unknown host", HOSTNAME)

