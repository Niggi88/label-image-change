import socket


CACHE = False
IMAGE_SIZE=2000
# DATASET_NAME="complex"
DATASET_NAME="small_set3"

HOSTNAME = socket.gethostname()

if HOSTNAME == "niggis-brain":
    DATASET_DIR = f"/media/fast/dataset/bildunterschied/test_mini/{DATASET_NAME}"
elif HOSTNAME == "KPKP":
    DATASET_DIR = f"/home/niklas/dataset/bildunterschied/test_mini/{DATASET_NAME}"
elif HOSTNAME == "sarah-XPS-15-9530":
    DATASET_DIR = f"/home/sarah/Documents/background_segmentation/relevant_sessions/store_8dbefa14-0515-47d3-aa69-470d9ee271b3"
else:
    raise Exception("Unknown host", HOSTNAME)

