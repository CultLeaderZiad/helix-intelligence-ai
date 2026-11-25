"""Admin knowledge base. Full platform admins only."""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_full_admin, get_current_user, get_db
from app.models.user import User
from app.core.config import settings
from app.services import kb_import, kb_service

router = APIRouter()
# Read-only view of the enabled articles for any signed-in user. Editing stays admin-only (router above).
public_router = APIRouter()


@public_router.get("")
async def public_articles(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return {"items": await kb_service.public_list(db)}


@public_router.get("/search")
async def public_article_search(q: str = Query("", max_length=200), db: AsyncSession = Depends(get_db),
                                user: User = Depends(get_current_user)):
    return {"items": await kb_service.public_search(db, q) if q.strip() else []}


@public_router.get("/{document_id}")
async def public_article(document_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await kb_service.public_document(db, document_id)


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


@router.post("/upload", status_code=201)
async def upload_files(files: List[UploadFile] = File(...), title: Optional[str] = Form(None),
                       db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_full_admin)):
    """.md, .txt and .zip files, read fully on the server. Each text file becomes its own document."""
    uploads = []
    for upload in files[: kb_import.MAX_FILES_PER_REQUEST + 1]:
        name = upload.filename or ""
        limit = settings.KB_MAX_ZIP_BYTES if name.lower().endswith(".zip") else settings.KB_MAX_FILE_BYTES
        raw = await upload.read(limit + 1)
        if len(raw) > limit:
            raise HTTPException(status_code=413, detail={"code": "kb_file_too_large", "message": f"{name or 'A file'} is larger than {limit} bytes."})
        uploads.append((name, raw))
    return await kb_import.import_files(db, admin.id, uploads, title)


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
