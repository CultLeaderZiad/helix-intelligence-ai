from pydantic import BaseModel
from typing import List, Optional

class Pattern(BaseModel):
    id: str
    label: str
    family: str
    prevalence: float
    # Null means the product has no observed performance lift for this pattern.
    lift_index: Optional[float] = None
    model_version: Optional[str] = None
    evidence_creative_ids: List[str] = []

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
    key_elements: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None

