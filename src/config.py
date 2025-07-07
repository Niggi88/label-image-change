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
else:
    raise Exception("Unknown host", HOSTNAME)

