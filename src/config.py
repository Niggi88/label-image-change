import socket


CACHE = True
IMAGE_SIZE=2000
UI_SCALING=1.5
FONT_SCALING=1.5
SERVER_AVAILABLE = None
SERVER = "http://172.30.20.31:8010/"

# DATASET_NAME="complex"
DATASET_NAME="tmp"

HOSTNAME = socket.gethostname()

if HOSTNAME == "niggis-brain":
    DATASET_NAME="tmp"
    DATASET_DIR = f"/media/fast/dataset/bildunterschied/test_mini/new_label_tool/{DATASET_NAME}"
    USERNAME = "niklas"
elif HOSTNAME == "niklas-XPS-15-9530":
    DATASET_NAME="dev"
    DATASET_DIR = f"/home/niklas/dataset/bildunterschied/{DATASET_NAME}"
    USERNAME = "niklas"
elif HOSTNAME == "sarah-XPS-15-9530":
    USERNAME = "sarah"
    DATASET_NAME = "small_relevant_sessions"
    # DATASET_DIR = f"/home/sarah/Documents/background_segmentation/{DATASET_NAME}"
    DATASET_DIR = f"/home/sarah/Documents/background_segmentation/{DATASET_NAME}"

elif HOSTNAME == "NB-ENDRES":
    USERNAME = "sarah_windoof"
    DATASET_NAME = "example_sessions"
    # DATASET_DIR = f"/home/sarah/Documents/background_segmentation/{DATASET_NAME}"
    DATASET_DIR = rf"C:\Users\sarah.endres\Documents\{DATASET_NAME}"

else:
    raise Exception("Unknown host", HOSTNAME)

