import json
from pathlib import Path

# ---- CONFIG ----
ANNOTATION_BASE = Path("home/sarah/labeldata")
CARREFOUR_DATA = Path("/opt/datasets/carrefour-change-data/santiago_20250801-20250816")
EDEKA_DATA = Path("/opt/datasets/head_and_shoulders_santiago/head_and_shoulders_sub_santiago/raw")

ALL_DATA = [CARREFOUR_DATA, EDEKA_DATA]
USER = "santiago"
# ----------------


def extract_session_from_path(im_path: str):
    """
    input:  store_xxx/session_xxx/63-uuid_top_0.jpeg
    return: ("store_xxx", "session_xxx", image_index:int)
    """
    p = Path(im_path)
    store = p.parts[-3]
    session = p.parts[-2]

    # dateiname beginnt mit z.B. "63-uuid.jpeg"
    index = int(p.name.split("-")[0])

    return store, session, index


def find_original_session_folder(store, session):
    """
    Findet den Ordner:
    /opt/datasets/carrefour-change-data/<user_YYYYMMDD-range>/
        store_xxx/session_xxx
    """
    for base in ALL_DATA:
        ss = base / store / session
        if ss.exists():
            return ss

    return None


def load_json_files():
    """Alle JSON-Annotationen eines Users laden."""
    user_dir = ANNOTATION_BASE / USER
    return list(user_dir.glob("*.json"))


def main():
    json_files = load_json_files()

    if not json_files:
        print("No JSON files found.")
        return

    print(f"Found {len(json_files)} annotation files for user {USER}.\n")

    all_reports = []
    found_sessions = set()
    missing_sessions = set()

    for jf in json_files:
        data = json.loads(jf.read_text())

        # JSON kann {"_meta":..., "0":{...}, "1":{...}} ODER {"_meta":..., "items":{...}}
        items = data.get("items", {k: v for k, v in data.items() if k != "_meta"})

        for pid, entry in items.items():
            im1 = entry.get("im1_path")
            im2 = entry.get("im2_path")

            if not im1 or not im2:
                continue

            if im1 == im2:
                # DUPLICATE FOUND
                store, session, idx = extract_session_from_path(im1)

                original_folder = find_original_session_folder(store, session)

                session_key = (store, session)

                if original_folder is None:
                    print(f"⚠ No original folder found for {store}/{session}")
                    missing_sessions.add(session_key)
                    continue
                else:
                    found_sessions.add(session_key)

                # originelle Bilder lesen
                all_imgs = sorted(
                    original_folder.glob("*.jpeg"),
                    key=lambda f: int(f.name.split("-")[0])
                )

                # korrekte Paarbilder sollten idx und idx+1 sein
                correct1 = next((p for p in all_imgs if p.name.startswith(f"{idx}-")), None)
                correct2 = next((p for p in all_imgs if p.name.startswith(f"{idx+1}-")), None)

                all_reports.append({
                    "json_file": str(jf),
                    "pair_id": pid,
                    "stored_im1": im1,
                    "stored_im2": im2,
                    "store": store,
                    "session": session,
                    "image_index": idx,
                    "correct_im1": str(correct1) if correct1 else None,
                    "correct_im2": str(correct2) if correct2 else None
                })

    # ---- Ausgabe ----
    print("\n==================== DUPLICATE REPORT =====================\n")

    if not all_reports:
        print("No duplicates found!")
        return

    for rep in all_reports[:10]:
        print(f"JSON: {rep['json_file']}")
        print(f" Pair ID: {rep['pair_id']}")
        print(f" Duplicate stored:")
        print(f"   im1 = {rep['stored_im1']}")
        print(f"   im2 = {rep['stored_im2']}  (duplicate!)")
        print(f" Original session folder:")
        print(f"   store = {rep['store']}")
        print(f"   session = {rep['session']}")
        print(f" Image index = {rep['image_index']}")
        print(f" Correct should be:")
        print(f"   {rep['correct_im1']}")
        print(f"   {rep['correct_im2']}")
        print("-" * 80)

    print(f"\nTotal duplicates found: {len(all_reports)}")
    print(f"total of missing sessions: {len(missing_sessions)}")
    print(f"total found sessions: {len(found_sessions)}")

if __name__ == "__main__":
    main()
