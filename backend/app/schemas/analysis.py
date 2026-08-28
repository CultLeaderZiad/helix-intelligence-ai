from pydantic import BaseModel
from typing import List

class Pattern(BaseModel):
    id: str
    label: str
    family: str
    prevalence: float
    lift_index: float

class Insight(BaseModel):
    id: str
    creative_id: str
    kind: str
    title: str
    summary: str
    confidence: float
    evidence_creative_ids: List[str]
    generated_at: str
    model_version: str
