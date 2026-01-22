from dataclasses import dataclass
from typing import List, Optional, Literal, Dict, Any
from tkinter import messagebox


PairState = Literal[
    "nothing", "chaos", "no_annotation", "added", "annotated", "edge_case"
]

VALID_PAIR_STATES = {
    "nothing", "chaos", "no_annotation", "added", "annotated", "edge_case"
}

STATES_REQUIRE_BOXES = {"added", "annotated"}

ANNOTATION_TYPES = {
    "item_added", "item_removed"
}
# -----------------------------
# Datenklassen
# -----------------------------

@dataclass
class Box:
    x1: int
    y1: int
    x2: int
    y2: int
    annotation_type: str


@dataclass
class PreviousRecord:
    pair_state: PairState
    boxes: List[Box]
    annotator: Optional[str]
    reviewer: Optional[str]
    timestampOriginalAnnotation: Optional[str]


@dataclass
class ResultRecord:
    pair_state: PairState
    boxes: List[Box]
    im1_path: str
    im2_path: str
    previously: Optional[PreviousRecord]


# -----------------------------
# Verifier
# -----------------------------

class DataVerifier:

    @staticmethod
    def check_valid_pair_state(ps: str) -> PairState:
        if ps not in VALID_PAIR_STATES:
            messagebox.showerror(
                "Invalid Data",
                f"Invalid pair_state: {ps}. Must be one of {VALID_PAIR_STATES}."
            )
            raise ValueError(f"Invalid pair_state: {ps}")
        return ps  # type: ignore

    @staticmethod
    def check_boxes_vs_state(pair_state: PairState, boxes: List[Box]) -> List[Box]:
        if pair_state in STATES_REQUIRE_BOXES and not boxes:
            messagebox.showerror(
                "Invalid Data",
                f"pair_state={pair_state} requires boxes, but none were provided."
            )
            raise ValueError(f"pair_state={pair_state} requires boxes")

        if pair_state not in STATES_REQUIRE_BOXES and boxes:
            messagebox.showerror(
                "Invalid Data",
                f"pair_state={pair_state} must not have boxes, but boxes were provided."
            )
            raise ValueError(f"pair_state={pair_state} must not have boxes")

        return boxes

    @staticmethod
    def check_boxes_annotation_type(boxes: List[Box]) -> None:
        for box in boxes:
            if box.annotation_type not in ANNOTATION_TYPES:
                messagebox.showerror(
                    "Invalid Data",
                    f"Invalid annotation_type: {box.annotation_type}. Must be one of {ANNOTATION_TYPES}."
                )
                raise ValueError(
                    f"Invalid annotation_type: {box.annotation_type}"
                )
            
    @staticmethod
    def images_must_differ(im1: str, im2: str) -> str:
        if im1 == im2:
            messagebox.showerror(
                "Invalid Data",
                "im1_path and im2_path must differ."
            )
            raise ValueError("im1_path and im2_path must differ")
        return im2

    @classmethod
    def verify_previous_record(cls, data: Dict[str, Any]) -> PreviousRecord:
        ps = cls.check_valid_pair_state(data["pair_state"])
        boxes = data.get("boxes", [])
        cls.check_boxes_vs_state(ps, boxes)

        return PreviousRecord(
            pair_state=ps,
            boxes=boxes,
            annotator=data.get("annotator"),
            reviewer=data.get("reviewer"),
            timestampOriginalAnnotation=data.get("timestampOriginalAnnotation"),
        )

    @classmethod
    def verify_result_record(cls, data: Dict[str, Any]) -> ResultRecord:
        ps = cls.check_valid_pair_state(data["pair_state"])
        boxes = data.get("boxes", [])
        # cls.check_boxes_vs_state(ps, boxes)
        # cls.check_boxes_annotation_type(boxes)

        im1 = data["im1_path"]
        im2 = cls.images_must_differ(im1, data["im2_path"])

        previously_data = data.get("previously")
        previously = (
            cls.verify_previous_record(previously_data)
            if previously_data
            else None
        )

        return ResultRecord(
            pair_state=ps,
            boxes=boxes,
            im1_path=im1,
            im2_path=im2,
            previously=previously,
        )
