from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import json
import pandas as pd



VALID_PAIR_STATES = {
    "annotated",
    "nothing",
    "chaos",
    "no_annotation",
    "edge_case",
}

@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float
    annotation_type: str
    box_id: str
        
    @classmethod
    def from_dict(cls, dict):
        return cls(
            x1=dict["x1"],
            y1=dict["y1"],
            x2=dict["x2"],
            y2=dict["y2"],
            annotation_type=dict["annotation_type"],
            box_id=dict["pair_id"],
        )

@dataclass
class Annotation:
    pair_state: str
    boxes: List[BoundingBox]
    annotator: Optional[str]

    def __post_init__(self):
        if self.pair_state not in VALID_PAIR_STATES:
            raise ValueError(
                f"invalid pair_state: {self.pair_state}"
            )
        
        if self.pair_state == "annotated" and not self.boxes:
            raise ValueError(
                "annotated but no boxes"
            )
        
    @classmethod
    def from_dict(cls, dict):
        boxes = [BoundingBox.from_dict(b) for b in dict.get("boxes", [])]
        return cls(
            pair_state=dict.get("pair_state"),
            boxes=boxes,
            annotator=dict.get("annotator"),
        )


@dataclass
class ModelPrediction(Annotation):
    confidence: float

    @classmethod
    def from_dict(cls, dict):
        base = Annotation.from_dict(dict)
        return cls(
            pair_state=base.pair_state,
            boxes=base.boxes,
            annotator=dict.get("model_name"),
            confidence=dict.get("confidence"),
        )

@dataclass
class ImagePair:
    pair_id: str
    image1_path: Path
    image2_path: Path

    original: Optional[Annotation]
    review: Optional[Annotation] = None
    model_prediction: Optional[ModelPrediction] = None


    @classmethod
    def read_json(cls, json_path):

        with open(json_path) as f:
            raw = json.load(f)

        pairs = {}

        for pair_id, data in raw.items():
            if pair_id == "_meta":
                continue

            # pairs[pair_id] = self.get_pair_annotation(pair_id, data)

            pair = cls.from_dict(data)
            pairs[pair.pair_id] = pair

        return pairs
            
    

    # @classmethod
    # def get_pair_annotation(self, data: dict):

        
    #     self.image1_path = data["im1_path"]
    #     self.image2_path = data["im2_path"]

    #     self.pair_id = self.make_key_from_im_path(self.image1_path)

    #     if "previously" in data:
    #         previous_pair = data["previously"]
    #         self.original.pair_state = previous_pair["pair_state"]
    #         self.original.annotator = previous_pair["annotator"]
    #         review_pair = data
    #         self.review.pair_state = review_pair["pair_state"]
    #         self.review.annotator = previous_pair["reviewer"]
    #         model_pair = data["model_prediction"]
    #         self.model_prediction.pair_state = model_pair["pair_state"]
    #         self.model_prediction.annotator = model_pair["model_name"]

    #     else:
    #         self.original.pair_state = data["pair_state"]
    #         self.original.annotator = data["annotator"]
    #         self.review = None
    #         self.model_prediction = None


    @classmethod
    def from_dict(cls, data):

        im1 = Path(data["im1_path"])
        im2 = Path(data["im2_path"])

        computed_id = cls.make_key_from_im_path(data["im1_path"])

        if "previously" in data:
            original = Annotation.from_dict(data["previously"])
            review = Annotation.from_dict(data)
            model = ModelPrediction.from_dict(data["model_predicition"])

        else:
            original = Annotation.from_dict(data)
            review = None
            model = None

        return cls(
            pair_id=computed_id,
            image1_path=im1,
            image2_path=im2,
            original=original,
            review=review,
            model_prediction=model,
        )

    @staticmethod
    def make_key_from_im_path(im_path):
        p = Path(im_path)

        parts = p.parts
        store = next(part for part in parts if part.startswith("store_"))
        session = next(part for part in parts if part.startswith("session_"))

        filename = p.stem
        index = filename.split("-")[0]

        return f"{store}/{session}|{index}"
    

# für inconsistent results
# store_20722c31-f069-4a2e-83c7-a8e79d8dd4a5/session_c984920e-b5ab-439d-9310-9b40df4afdbb|31"

# für change data
# "im1_path": "store_eb36deb2-bcab-4f89-8536-2dd6e0a0d7aa/session_e0d90e6a-d87a-4bae-8458-40596b1a66ed/0-d07d303b-797b-4e5c-96e1-72d0e4e8970b_top_0.jpeg"