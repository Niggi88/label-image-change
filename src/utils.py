from PIL import Image
import requests
import os
import json
import config
try:
    resample_filter = Image.Resampling.LANCZOS
except AttributeError:
    resample_filter = Image.ANTIALIAS

def resize_with_aspect_ratio(pil_img, base_width=None, base_height=None):
    """
    Resize an image while maintaining its aspect ratio.

    Args:
        pil_img: A Pillow Image object.
        base_width: The desired width while maintaining aspect ratio (optional).
        base_height: The desired height while maintaining aspect ratio (optional).

    Returns:
        A resized Pillow Image object.
    """
    original_width, original_height = pil_img.size

    if base_width is not None:  # Resize by width
        w_ratio = base_width / float(original_width)
        new_width = base_width
        new_height = int((original_height * w_ratio))
    elif base_height is not None:  # Resize by height
        h_ratio = base_height / float(original_height)
        new_width = int((original_width * h_ratio))
        new_height = base_height
    else:
        raise ValueError("You must specify either base_width or base_height.")

    return pil_img.resize((new_width, new_height), resample_filter)


def report_annotation(user, class_name="unknown", pair_id=None):
    annotation_payload = {
        "username": user,
        "className": class_name,
        "pairId": pair_id,
        "count": 1
    }

    # ⛔ Server bereits als nicht verfügbar markiert?
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
        config.SERVER_AVAILABLE = True  # ✅ Server OK
    except Exception as e:
        print(f"[WARN] Could not send annotation, caching: {e}")
        config.SERVER_AVAILABLE = False  # ❌ Server als offline markieren
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
