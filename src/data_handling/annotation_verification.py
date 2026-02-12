from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import json
import pandas as pd

@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float
    annotation_type: str
    box_id: str

@dataclass
class Annotation:
    pair_state: str
    boxes: List[BoundingBox]
    annotator: Optional[str]

    def get_pair_state(self, pair):
        self.pair_state = pair["pair_state"]
        self.boxes = pair["boxes"]

    def get_annotator(self, pair):
        self.annotator = pair["annotator"]

    def get_reviewer(self, pair):
        self.annotator = pair["reviewer"]

    def get_model(self, pair):
        self.annotator = pair["model_name"]


@dataclass
class ModelPrediction(Annotation):
    confidence: float

@dataclass
class ImagePair:
    pair_id: str
    image1_path: Path
    image2_path: Path

    original: Optional[Annotation]
    review: Optional[Annotation] = None
    model_prediction: Optional[ModelPrediction] = None

    @classmethod
    def read_json(self, json_path):

        with open(json_path) as f:
            raw = json.load(f)

        pairs = {}

        for pair_id, data in raw.items():
            if pair_id == "_meta":
                continue

            pairs[pair_id] = self.get_pair_annotation(pair_id, data)

        return pairs
            
    

    @classmethod
    def get_pair_annotation(self, data: dict):

        
        self.image1_path = data["im1_path"]
        self.image2_path = data["im2_path"]

        self.pair_id = self.make_key_from_im_path(self.image1_path)

        if "previously" in data:
            previous_pair = data["previously"]
            self.original.pair_state = previous_pair["pair_state"]
            self.original.annotator = previous_pair["annotator"]
            review_pair = data
            self.review.pair_state = review_pair["pair_state"]
            self.review.annotator = previous_pair["reviewer"]
            model_pair = data["model_prediction"]
            self.model_prediction.pair_state = model_pair["pair_state"]
            self.model_prediction.annotator = model_pair["model_name"]

        else:
            self.original.pair_state = data["pair_state"]
            self.original.annotator = data["annotator"]
            self.review = None
            self.model_prediction = None


    @staticmethod
    def make_key_from_im_path(im_path):
        p = Path(im_path)

        store = p.parts[0]
        session = p.parts[1]

        filename = p.stem  # ohne .jpeg
        index = filename.split("-")[0]  # Zahl vor dem ersten "-"

        return f"{store}/{session}|{index}"
    

# für inconsistent results
# store_20722c31-f069-4a2e-83c7-a8e79d8dd4a5/session_c984920e-b5ab-439d-9310-9b40df4afdbb|31"

# für change data
# "im1_path": "store_eb36deb2-bcab-4f89-8536-2dd6e0a0d7aa/session_e0d90e6a-d87a-4bae-8458-40596b1a66ed/0-d07d303b-797b-4e5c-96e1-72d0e4e8970b_top_0.jpeg"