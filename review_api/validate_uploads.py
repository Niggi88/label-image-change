# validation/results.py
from pydantic import BaseModel, field_validator, ValidationError
from typing import List, Optional, Literal, Dict, Any

VALID_PAIR_STATES = {
    "nothing", "chaos", "no_annotation", "added", "annotated", "edge_case"
}

STATES_REQUIRE_BOXES = {"added", "annotated"}

PairState = Literal[
    "nothing", "chaos", "no_annotation", "added", "annotated", "edge_case"
]


class Box(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    annotation_type: str

class PreviousRecord(BaseModel):
    pair_state: PairState
    boxes: List[Box]
    annotator: str
    reviewer: str
    timestampOriginalAnnotation: str

    @field_validator("boxes", mode="after")
    @classmethod
    def check_boxes_vs_state(cls, boxes, info):
        ps = info.data["pair_state"]

        if ps in STATES_REQUIRE_BOXES and not boxes:
            raise ValueError(f"pair_state={ps} requires boxes")

        if ps not in STATES_REQUIRE_BOXES and boxes:
            raise ValueError(f"pair_state={ps} must have empty boxes")

        return boxes

class ResultRecord(BaseModel):
    pair_state: PairState
    boxes: List[Box]
    im1_path: str
    im2_path: str
    previously: PreviousRecord

    @field_validator("boxes", mode="after")
    @classmethod
    def check_boxes_vs_state(cls, boxes, info):
        ps = info.data["pair_state"]

        if ps in STATES_REQUIRE_BOXES and not boxes:
            raise ValueError(f"pair_state={ps} requires boxes")

        if ps not in STATES_REQUIRE_BOXES and boxes:
            raise ValueError(f"pair_state={ps} must have empty boxes")

        return boxes

    @field_validator("im2_path")
    @classmethod
    def images_must_differ(cls, im2, info):
        im1 = info.data.get("im1_path")
        if im1 and im2 and im1 == im2:
            raise ValueError("im1_path and im2_path must differ")
        return im2


def validate_results_payload(
    batch: Dict[str, Any],
    results: Dict[str, Any],
):
    batch_keys = {
        f"{it['store_session_path']}|{int(it['pair_id'])}"
        for it in batch.get("items", [])
    }

    items = results.get("items")
    if not isinstance(items, dict):
        raise ValueError("results.items must be a dict")

    for key, value in items.items():
        if key not in batch_keys:
            raise ValueError(f"{key} not part of batch")

        try:
            ResultRecord.model_validate(value)
        except ValidationError as e:
            raise ValueError(f"{key}: {e}") from e
