from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.services import playbook_service

router = APIRouter()

class PlaybookCompileRequest(BaseModel):
    brand_name: str
    query: str
    job_id: Optional[str] = None
    custom_title: Optional[str] = None

@router.post("")
async def compile_playbook(
    body: PlaybookCompileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    playbook = await playbook_service.compile_playbook(
        db=db,
        user=current_user,
        brand_name=body.brand_name,
        query=body.query,
        job_id=body.job_id,
        custom_title=body.custom_title
    )
    return {
        "id": playbook.id,
        "public_id": playbook.public_id,
        "share_url": f"/playbook/{playbook.public_id}",
        "brand_name": playbook.brand_name,
        "title": playbook.title,
        "created_at": playbook.created_at.isoformat() if playbook.created_at else ""
    }

@router.get("")
async def list_playbooks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await playbook_service.list_user_playbooks(db, current_user.id)

@router.get("/public/{public_id}")
async def get_public_playbook(
    public_id: str,
    db: AsyncSession = Depends(get_db)
):
    # Notice: NO current_user requirement -> public unauthenticated read-only endpoint
    return await playbook_service.get_public_playbook(db, public_id)
