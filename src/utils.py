from PIL import Image
import requests

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
    try:
        response = requests.post(
            "http://172.30.20.31:8010/api/annotate",
            json={
                "username": user,
                "className": class_name,
                "pairId": pair_id,
                "count": 1
            },
            timeout=1
        )
        print("[INFO] Reported annotation:", response.status_code)
    except Exception as e:
        print(f"[WARN] Could not send annotation count: {e}")

import requests



def already_annotated_on_server(username: str, pair_id: str) -> bool:
    try:
        response = requests.get("http://172.30.20.31:8010/api/stats", timeout=2)
        response.raise_for_status()
        data = response.json()

        user_data = data.get("users", {}).get(username, {})
        annotated_pairs = user_data.get("pairs", {})

        return pair_id in annotated_pairs
    except Exception as e:
        print(f"[WARN] Failed to check server annotation status: {e}")
        # Fallback: assume already annotated to be safe
        return True
