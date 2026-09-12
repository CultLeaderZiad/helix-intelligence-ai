from pydantic import BaseModel
from typing import List, Optional


class PersonaSegment(BaseModel):
    """A preset synthetic-audience persona used to rehearse a creative."""
    id: str
    label: str
    description: str


# Fixed preset personas. Deliberately not user-customizable yet — a small,
# well-specified set keeps the LLM's role-play grounded and keeps pricing
# predictable. Add personas here (and mirror the ids in the frontend mock)
# rather than accepting free-text audience descriptions from the client.
PRESET_SEGMENTS: List[PersonaSegment] = [
    PersonaSegment(
        id="price_sensitive_skeptic",
        label="Price-Sensitive Skeptic",
        description="Compares every claim to cheaper alternatives, distrusts superlatives, and looks for the catch before considering a purchase.",
    ),
    PersonaSegment(
        id="brand_loyalist",
        label="Existing Brand Loyalist",
        description="Already uses a competing or incumbent product, evaluates the ad against their current habit, and needs a concrete reason to switch.",
    ),
    PersonaSegment(
        id="trend_driven_gen_z",
        label="Trend-Driven Gen Z",
        description="Scrolls fast, judges within 2 seconds, values authenticity and humor over polish, and is quick to call out anything that feels like a generic ad.",
    ),
    PersonaSegment(
        id="busy_value_researcher",
        label="Busy Value-Conscious Researcher",
        description="Reads carefully but has little time, wants concrete specifics and proof over adjectives, and abandons ads that feel vague or exaggerated.",
    ),
    PersonaSegment(
        id="early_adopter_enthusiast",
        label="Early-Adopter Enthusiast",
        description="Excited by new products and novel claims, but has seen many ad gimmicks before and can spot hype that isn't backed by substance.",
    ),
    PersonaSegment(
        id="cautious_first_time_buyer",
        label="Cautious First-Time Buyer",
        description="Unfamiliar with the category, easily confused by jargon, and highly sensitive to anything that reads as risky, technical, or untrustworthy.",
    ),
]

PRESET_SEGMENTS_BY_ID = {s.id: s for s in PRESET_SEGMENTS}


class SimulationRequest(BaseModel):
    segment_ids: List[str]
    byok_key: Optional[str] = None
    byok_provider: Optional[str] = None


class SegmentReaction(BaseModel):
    segment_id: str
    segment_label: str
    appeal_score: float
    objections: List[str] = []
    confusing_claims: List[str] = []
    credibility_assessment: str
    compliance_risks: List[str] = []


class SimulationReport(BaseModel):
    id: str
    creative_id: str
    simulation_id: str
    # These are never real audience metrics — a synthetic-audience rehearsal
    # is a risk-catching tool, not a performance predictor. Every report is
    # visibly tagged so it can never be confused with real CTR/conversion data.
    data_source: str = "simulated"
    is_estimated: bool = True
    model_version: str
    assumptions: List[str] = []
    evidence_creative_ids: List[str] = []
    generated_at: str
    segment_reactions: List[SegmentReaction]
    recommended_angles: List[str] = []
