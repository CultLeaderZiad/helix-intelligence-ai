"""Admin knowledge base. Full platform admins only."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_full_admin, get_db
from app.models.user import User
from app.services import kb_service

router = APIRouter()


class KbUpload(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1)
    filename: Optional[str] = Field(None, max_length=200)


class KbStatus(BaseModel):
    enabled: bool


@router.get("")
async def list_documents(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_full_admin)):
    return {"items": await kb_service.list_documents(db)}


@router.post("", status_code=201)
async def upload_document(body: KbUpload, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_full_admin)):
    return await kb_service.upload(db, admin.id, body.title, body.text, body.filename)


@router.get("/audit")
async def audit_log(limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_db),
                    admin: User = Depends(get_current_full_admin)):
    return {"items": await kb_service.audit(db, limit)}


@router.get("/search")
async def search(q: str = Query(..., min_length=1, max_length=200), k: int = Query(5, ge=1, le=10),
                 db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_full_admin)):
    return {"items": await kb_service.search(db, q, k)}


@router.get("/{document_id}")
async def preview(document_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_full_admin)):
    return await kb_service.preview(db, document_id)


@router.patch("/{document_id}")
async def set_status(document_id: str, body: KbStatus, db: AsyncSession = Depends(get_db),
                     admin: User = Depends(get_current_full_admin)):
    return await kb_service.set_status(db, admin.id, document_id, body.enabled)


@router.delete("/{document_id}")
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_full_admin)):
    await kb_service.delete(db, admin.id, document_id)
    return {"ok": True}
