from pydantic import BaseModel
from typing import List, Optional

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
    evidence_creative_ids: List[str] = []
    generated_at: str
    model_version: str
    emotional_resonance: Optional[str] = None
    script_teardown: Optional[str] = None
    fatigue_prediction: Optional[str] = None

