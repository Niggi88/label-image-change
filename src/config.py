import socket


CACHE = True
IMAGE_SIZE=2000
# DATASET_NAME="complex"
DATASET_NAME="one"

HOSTNAME = socket.gethostname()

if HOSTNAME == "niggis-brain":
    DATASET_DIR = f"/media/fast/dataset/bildunterschied/test_mini/new_label_tool/{DATASET_NAME}"
elif HOSTNAME == "KPKP":
    DATASET_DIR = f"/home/niklas/dataset/bildunterschied/test_mini/{DATASET_NAME}"
elif HOSTNAME == "sarah-XPS-15-9530":
    DATASET_DIR = f"/home/sarah/Documents/background_segmentation/relevant_sessions"
else:
    raise Exception("Unknown host", HOSTNAME)

