import socket


CACHE = True
IMAGE_SIZE=2000
# DATASET_NAME="complex"
DATASET_NAME="tmp"

HOSTNAME = socket.gethostname()

if HOSTNAME == "niggis-brain":
    DATASET_DIR = f"/media/fast/dataset/bildunterschied/test_mini/new_label_tool/{DATASET_NAME}"
elif HOSTNAME == "KPKP":
    DATASET_DIR = f"/home/niklas/dataset/bildunterschied/test_mini/{DATASET_NAME}"
elif HOSTNAME == "sarah-XPS-15-9530":
    DATASET_NAME = "small_relevant_sessions"
    # DATASET_DIR = f"/home/sarah/Documents/background_segmentation/{DATASET_NAME}"
    DATASET_DIR = f"/home/sarah/Documents/background_segmentation/{DATASET_NAME}"
else:
    raise Exception("Unknown host", HOSTNAME)

