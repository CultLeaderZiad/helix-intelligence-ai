"""Guarded access to locally stored media.

This replaces the old ``StaticFiles`` mount, which served every file in the
uploads directory to anyone who could guess a name -- and names were guessable,
because they were ``{job_id}_{8 hex chars}``.

Access is granted two ways:

* a valid signature, which makes the URL a capability in the same way an S3
  presigned URL is. This is what newly stored files get, and it is the only
  option that works from an ``<img>`` tag, which cannot send an
  ``Authorization`` header.
* an authenticated caller who owns the media job that produced the file. This
  covers pre-existing files whose stored URL has no signature.

Anything else gets a 404 rather than a 403, so this endpoint cannot be used to
probe which filenames exist.

This router is transitional. Once R2 is configured, new media never lands here
and the route can be deleted along with the uploads directory.
"""

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.media_job import MediaGenerationJob
from app.models.user import User
from app.services.storage_service import UPLOAD_DIR, verify_local_signature

router = APIRouter()

NOT_FOUND = HTTPException(status_code=404, detail="Not found")


async def _authenticated_user(request: Request, token: Optional[str], db: AsyncSession) -> Optional[User]:
    """Resolve a user from a bearer header or a ?token= query parameter.

    Returns None instead of raising: a failed lookup here means "no owner
    access", which the caller turns into a 404.
    """
    raw = token
    if not raw:
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            raw = header[7:]
    if not raw:
        return None

    from app.core.security import verify_neon_token

    try:
        payload = await verify_neon_token(raw)
    except Exception:
        return None
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()


async def _user_owns_file(db: AsyncSession, user: User, filename: str) -> bool:
    if getattr(user, "role", None) in ("admin", "assistant-admin"):
        return True
    job = (
        await db.execute(
            select(MediaGenerationJob).where(
                MediaGenerationJob.user_id == user.id,
                MediaGenerationJob.result_url.like(f"%/{filename}%"),
            )
        )
    ).scalars().first()
    return job is not None


@router.get("/{filename}")
async def get_upload(
    filename: str,
    request: Request,
    sig: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    # Reject anything that is not a bare filename before it reaches the disk.
    if not filename or "/" in filename or "\\" in filename or filename.startswith("."):
        raise NOT_FOUND

    file_path = os.path.abspath(os.path.join(UPLOAD_DIR, filename))
    if os.path.commonpath([file_path, UPLOAD_DIR]) != UPLOAD_DIR:
        raise NOT_FOUND
    if not os.path.isfile(file_path):
        raise NOT_FOUND

    if not verify_local_signature(filename, sig):
        user = await _authenticated_user(request, token, db)
        if not user or not await _user_owns_file(db, user, filename):
            raise NOT_FOUND

    return FileResponse(file_path)
