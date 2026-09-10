from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.schemas.simulation import SimulationRequest, SimulationReport, PersonaSegment, PRESET_SEGMENTS
from app.services import simulation_service
from app.core.deps import get_db, get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/segments", response_model=List[PersonaSegment])
async def list_audience_segments():
    """Fixed preset synthetic-audience personas available to simulate against."""
    return PRESET_SEGMENTS


@router.post("/creatives/{creative_id}/simulate", response_model=SimulationReport)
async def simulate_creative(
    creative_id: str,
    request: SimulationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await simulation_service.simulate_creative_for_audiences(
        db,
        creative_id,
        request.segment_ids,
        current_user,
        request.byok_key,
        request.byok_provider,
    )
