# review_pair_registry.py
import json
from functools import lru_cache
from pathlib import Path

REVIEW_BATCH_DIR = Path(
    "/opt/datasets/change_detection/change_data/review_batches"
)

def _model_to_json_path(model_name: str) -> Path:

    if not model_name.endswith(".pth"):
        raise ValueError(f"Invalid model name: {model_name}")

    json_name = model_name.removesuffix(".pth") + ".json"
    return REVIEW_BATCH_DIR / json_name


@lru_cache(maxsize=None)
def _load_pairs(model_name: str) -> dict:
    json_path = _model_to_json_path(model_name)

    if not json_path.exists():
        raise FileNotFoundError(f"Review JSON not found: {json_path}")

    with json_path.open("r") as f:
        data = json.load(f)

    print(f"[REVIEW_REGISTRY] Loaded {len(data)} pairs for {model_name}")
    return data


# -------- Public API --------

def get_total_pairs(model_name: str) -> int:
    return len(_load_pairs(model_name))


def get_all_pair_ids(model_name: str) -> set[str]:
    return set(_load_pairs(model_name).keys())


def get_pair_ids_by_annotator(model_name: str, annotator: str) -> set[str]:
    data = _load_pairs(model_name)
    annotator_norm = annotator.strip().lower()

    return {
        pair_id
        for pair_id, entry in data.items()
        if isinstance(entry.get("annotated_by"), str)
           and entry["annotated_by"].strip().lower() == annotator_norm
    }
