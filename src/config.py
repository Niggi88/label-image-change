import socket


CACHE = True
IMAGE_SIZE=2000
UI_SCALING=1.5
FONT_SCALING=1.5
# DATASET_NAME="complex"
DATASET_NAME="gemuese_netz_sub"

HOSTNAME = socket.gethostname()

if HOSTNAME == "niggis-brain":
    DATASET_DIR = f"/media/fast/dataset/bildunterschied/labeling/{DATASET_NAME}"
    USERNAME = "niklas"
elif HOSTNAME == "KPKP":
    DATASET_DIR = f"/home/niklas/dataset/bildunterschied/test_mini/{DATASET_NAME}"
elif HOSTNAME == "sarah-XPS-15-9530":
    USERNAME = "sarah"
    DATASET_NAME = "test_highscore"
    # DATASET_DIR = f"/home/sarah/Documents/background_segmentation/{DATASET_NAME}"
    DATASET_DIR = f"/home/sarah/Documents/background_segmentation/{DATASET_NAME}"
else:
    raise Exception("Unknown host", HOSTNAME)

