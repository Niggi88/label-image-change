import socket



HOSTNAME = socket.gethostname()

if HOSTNAME == "niggis-brain":
    DATASET_DIR = "/media/fast/dataset/bildunterschied/test_mini/complex"
elif HOSTNAME == "KPKP":
    DATASET_DIR = "/home/niklas/dataset/bildunterschied/test_mini/complex"
else:
    raise Exception("Unknown host", HOSTNAME)


CACHE = False