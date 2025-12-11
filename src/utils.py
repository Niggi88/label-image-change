from PIL import Image
from pathlib import Path
import requests
import os
import json
from src import config
try:
    resample_filter = Image.Resampling.LANCZOS
except AttributeError:
    resample_filter = Image.ANTIALIAS


def make_relative_path(abs_path, dataset_root=None):
    """
    Return a path relative to the dataset root.
    If dataset_root is None, falls back to config.DATASET_DIR.
    """
    from config import DATASET_DIR  # local import to avoid stale globals
    root = Path(dataset_root or DATASET_DIR).resolve()
    return Path(abs_path).resolve().relative_to(root).as_posix()

def report_annotation(class_name="unknown", pair_id=None):
    annotation_payload = {
        "username": config.USERNAME,
        "className": class_name,
        "pairId": pair_id,
        "count": 1
    }

    if config.SERVER_AVAILABLE is False:
        print("[SKIP] Server offline, writing to cache")
        cache_annotation(annotation_payload)
        return

    try:
        response = requests.post(
            f"{config.SERVER}api/annotate",
            json=annotation_payload,
            timeout=1
        )
        response.raise_for_status()
        print("[INFO] Reported annotation:", response.status_code)
        config.SERVER_AVAILABLE = True 
    except Exception as e:
        print(f"[WARN] Could not send annotation, caching: {e}")
        config.SERVER_AVAILABLE = False
        cache_annotation(annotation_payload)


import requests



def already_annotated_on_server(username: str, pair_id: str) -> bool:
    try:
        response = requests.get(f"{config.SERVER}api/stats", timeout=2)
        response.raise_for_status()
        data = response.json()

        user_data = data.get("users", {}).get(username, {})
        annotated_pairs = user_data.get("pairs", {})

        return pair_id in annotated_pairs
    except Exception as e:
        print(f"[WARN] Failed to check server annotation status: {e}")
        # Fallback: assume already annotated to be safe
        return True


def cache_annotation(annotation):
    cache_file = "annotation_cache.json"
    try:
        cache = []
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                cache = json.load(f)
        cache.append(annotation)
        with open(cache_file, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to cache annotation: {e}")


from collections import defaultdict

def flush_annotation_cache():
    cache_file = "annotation_cache.json"
    if not os.path.exists(cache_file):
        return

    with open(cache_file) as f:
        cached = json.load(f)

    # Aggregate by (username, pairId) → use the latest className
    grouped = {}
    for annotation in cached:
        key = (annotation["username"], annotation["pairId"])
        grouped[key] = annotation  # Latest annotation overrides previous ones

    remaining = []
    for ann in grouped.values():
        try:
            res = requests.post(f"{config.SERVER}api/annotate", json=ann)
            res.raise_for_status()
        except Exception as e:
            print(f"[WARN] Failed to upload cached annotation: {e}")
            remaining.append(ann)

    with open(cache_file, "w") as f:
        json.dump(remaining, f, indent=2)



## for inconsistent ##

def report_inconsistent_review(pair_id, predicted, expected, reviewer, decision, model_name):
    payload = {
        "pairId": pair_id,
        "predicted": predicted,
        "expected": expected,
        "reviewer": reviewer,
        "decision": decision,
        "modelName": model_name
    }

    try:
        response = requests.post(
            f"{config.SERVER}/api/inconsistent/review",
            json=payload,
            timeout=1
        )
        response.raise_for_status()
        print("[INFO] Sent inconsistent review for", pair_id)
    except Exception as e:
        print("[WARN] Failed to send inconsistent review:", e)
