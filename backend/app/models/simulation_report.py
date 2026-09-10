from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from app.db.base import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class SimulationReport(Base):
    """Persisted synthetic-audience rehearsal result for a creative.

    Always simulated LLM persona role-play — never a real performance
    prediction. `data_source`/`is_estimated` are stored (not derived) so an
    honest label survives even if defaults change later.
    """
    __tablename__ = "simulation_reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    creative_id = Column(String, ForeignKey("creatives.id"), nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    data_source = Column(String, nullable=False, default="simulated")
    is_estimated = Column(Boolean, nullable=False, default=True)
    model_version = Column(String, nullable=True)
    assumptions = Column(JSON, nullable=True)
    evidence_creative_ids = Column(JSON, nullable=True)
    segment_reactions = Column(JSON, nullable=True)
    recommended_angles = Column(JSON, nullable=True)
    generated_at = Column(String, nullable=True)
