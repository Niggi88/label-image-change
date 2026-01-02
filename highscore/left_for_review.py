from review_pair_registry import get_all_pair_ids, get_pair_ids_by_annotator
from review_db import get_reviewed_pair_ids_by_model, get_reviewed_pair_ids_by_annotator_and_model


def get_left_for_review_pair_ids(model_name: str) -> set[str]:
    all_pairs = get_all_pair_ids(model_name)
    reviewed_pairs = get_reviewed_pair_ids_by_model(model_name)

    return all_pairs - reviewed_pairs


def get_left_for_review_count(model_name: str) -> int:
    return len(get_left_for_review_pair_ids(model_name))


def get_annotator_review_progress(model_name: str, annotator: str) -> dict:
    all_pairs = get_pair_ids_by_annotator(model_name, annotator)
    reviewed = get_reviewed_pair_ids_by_annotator_and_model(model_name, annotator)

    total = len(all_pairs)
    reviewed_cnt = len(reviewed)
    left = total - reviewed_cnt

    return {
        "annotator": annotator,
        "total": total,
        "reviewed": reviewed_cnt,
        "left": left,
        "progress": reviewed_cnt / total if total > 0 else 0.0
    }