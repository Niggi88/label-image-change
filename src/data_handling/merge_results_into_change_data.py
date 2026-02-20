import json
import glob
import os
from copy import deepcopy
from datetime import datetime
import tempfile

'''
how to:
1) backup machen von allen user folder in change_data
    - soll dann da liegen: /opt/datasets/change_detection/change_data_DD-MM-YYYY.bak
2) Pfade anpassen
    - REVIEW_DIR = dort wo die results liegen: /opt/datasets/change_detection/change_data/review_batches/batches_MODEL_NAME/results_MODEL_NAME
    - LOG_DIR = dort wo backup liegt
3) DRY_RUN
    = TRUE: sanity check, am ende sollten so viele daten processed sein wie extractor script extracted hat
    = FALSE: kopiert die daten

4) finito :)
'''



REVIEW_DIR = "/opt/datasets/change_detection/change_data/review_batches/batches_main_real_data_images_v3_0_santiago_3cl_data-refinement/results_main_real_data_images_v3_0_santiago_3cl_data-refinement"
USER_ROOT  = "/opt/datasets/change_detection/change_data"
USERS = ["almas", "niklas", "santiago", "sarah"]

RUN_TS = datetime.now().strftime("%Y%m%d")
LOG_FILE = f"/opt/datasets/change_detection/change_data_11-02-2026.bak/change_log_{RUN_TS}.json"
DRY_RUN = False


def normalize_image_path(p):
    if not isinstance(p, str):
        return p
    if "/images/" in p:
        p = p.split("/images/", 1)[1]
    return p.lstrip("/")

def replace_if_added(d: dict):
    """
    Replace pair_state == 'added' → 'annotated' in dict d if present.
    """
    if not isinstance(d, dict):
        return

    if d.get("pair_state") == "added":
        if not DRY_RUN:
            d["pair_state"] = "annotated"


def safe_write_json(filepath, data):
    dirpath = os.path.dirname(filepath)

    with tempfile.NamedTemporaryFile(
        "w",
        dir=dirpath,
        delete=False
    ) as tmp:

        json.dump(data, tmp, indent=4)
        tmp.flush()
        os.fsync(tmp.fileno())

        temp_name = tmp.name

    os.replace(temp_name, filepath)


def write_log(user_file, item_id, before, after, review_ts):
    log_entry = {
        "log_timestamp": datetime.now().isoformat(),
        "review_timestamp": review_ts,
        "user_file": user_file,
        "item_id": item_id,
        "before": before,
        "after": after,
    }

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as lf:
            try:
                log_data = json.load(lf)
            except json.JSONDecodeError:
                log_data = []
    else:
        log_data = []

    log_data.append(log_entry)

    safe_write_json(LOG_FILE, log_data)



def find_user_file(store_id, session_id):
    for user in USERS:
        user_root = os.path.join(USER_ROOT, user)
        if not os.path.isdir(user_root):
            continue

        pattern = os.path.join(
            user_root,
            "**",
            f"{store_id}__{session_id}*.json"
        )
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]
    return None


for review_file in glob.glob(os.path.join(REVIEW_DIR, "*.json")):
    with open(review_file, "r") as f:
        review_data = json.load(f)

    items = review_data.get("items", {})

counter = 0
total_pairs = 0
for review_file in glob.glob(os.path.join(REVIEW_DIR, "*.json")):
    with open(review_file, "r") as f:
        review_data = json.load(f)

    review_ts = review_data.get("_meta", {}).get("timestamp")
    items = review_data.get("items", {})

    for key, review_entry in items.items():
        counter +=1
        try:
            left, item_id = key.split("|", 1)
            store_id, session_id = left.split("/", 1)

            user_file = find_user_file(store_id, session_id)
            if not user_file:
                print(f"[WARN] No user file for {store_id}/{session_id}")
                continue

            with open(user_file, "r") as uf:
                user_data = json.load(uf)

            if item_id not in user_data:
                print(f"[WARN] Item {item_id} missing in {user_file}")
                continue

            # --- sanity check paths ---
            assert normalize_image_path(user_data[item_id]["im1_path"]) == normalize_image_path(review_entry["im1_path"])
            assert normalize_image_path(user_data[item_id]["im2_path"]) == normalize_image_path(review_entry["im2_path"])

            # --- FULL REPLACEMENT ---
            new_entry = deepcopy(review_entry)

            # normalize paths
            new_entry["im1_path"] = normalize_image_path(new_entry.get("im1_path"))
            new_entry["im2_path"] = normalize_image_path(new_entry.get("im2_path"))

            # ADD REVIEW TIMESTAMP
            if review_ts:
                new_entry["timestamp_reviewed"] = review_ts

            if item_id == "_meta" or not isinstance(review_entry, dict):
                continue

            total_pairs += 1

            # 1. top-level
            replace_if_added(new_entry)

            # 2. previously
            if "previously" in new_entry:
                replace_if_added(new_entry["previously"])

            # 3. model_predicition
            if "model_predicition" in new_entry:
                replace_if_added(new_entry["model_predicition"])


            if DRY_RUN:
                print(f"[DRY-RUN] Would fully replace {user_file} | item {item_id}")
            else:
                entry_before = deepcopy(user_data[item_id])
                user_data[item_id] = new_entry
                safe_write_json(user_file, user_data)

                # hier log.json
                # entry before -> entry after
                write_log(
                    user_file=user_file,
                    item_id=item_id,
                    before=entry_before,
                    after=new_entry,
                    review_ts=review_ts
                )

                print(f"[OK] Fully replaced {user_file} | item {item_id}")


        except Exception as e:
            print(f"[ERROR] {key} → {e}")

    print("replaced: ", counter)