from fastapi import APIRouter
from app.services.media.higgsfield_provider import HiggsfieldProvider

router = APIRouter()
provider = HiggsfieldProvider()

@router.get("/health")
async def higgsfield_health_check():
    """
    Public diagnostic endpoint to verify Higgsfield credentials against {HIGGSFIELD_BASE_URL}/models.
    Safe for production monitoring. Never leaks keys or Authorization headers.
    """
    return await provider.get_health()

@router.get("/models")
async def list_higgsfield_models():
    """
    Returns available semantic capabilities and mappings.
    """
    return await provider.list_models()
