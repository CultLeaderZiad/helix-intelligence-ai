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

from app.core.deps import authenticate_bearer, get_db
from app.models.media_job import MediaGenerationJob
from app.models.organization import Organization
from app.models.user import User
from app.services.storage_service import UPLOAD_DIR, media_response_headers, verify_capability

router = APIRouter()

NOT_FOUND = HTTPException(status_code=404, detail="Not found")


async def _authenticated_user(request: Request, db: AsyncSession) -> Optional[User]:
    """Resolve a user from the Authorization header.

    Bearer tokens in the query string are ignored. A failed lookup means
    "no owner access", which the caller turns into a 404.
    """
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    raw = header[7:]
    if not raw:
        return None
    try:
        return await authenticate_bearer(db, raw)
    except HTTPException as exc:
        if exc.status_code == 403:
            raise NOT_FOUND
        return None


def _token_version(user: User) -> str:
    metadata = getattr(user, "signup_metadata", None) or {}
    try:
        return str(int(metadata.get("token_version", 1)))
    except (TypeError, ValueError):
        return "1"


async def _user_owns_file(db: AsyncSession, user: User, filename: str) -> bool:
    from app.core.tenancy import get_user_org_ids

    org_ids = await get_user_org_ids(db, user)
    # API-key scope is applied before the admin bypass inside get_user_org_ids.
    if org_ids is None:
        return True
    job = (
        await db.execute(
            select(MediaGenerationJob).where(
                MediaGenerationJob.org_id.in_(org_ids),
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
    exp: Optional[str] = Query(None),
    org: Optional[str] = Query(None),
    uid: Optional[str] = Query(None),
    ver: Optional[str] = Query(None),
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

    # `token` used to carry a full JWT. It is no longer an access credential.
    del token
    capability_ok = verify_capability(filename, sig, exp, org or "", uid or "", ver or "")
    if capability_ok and uid:
        owner = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
        if owner is None or _token_version(owner) != str(ver or "") or getattr(owner, "is_banned", False):
            capability_ok = False
    if capability_ok and org:
        organization = (await db.execute(select(Organization).where(Organization.id == org))).scalar_one_or_none()
        if organization is None or (organization.status or "active") != "active":
            capability_ok = False
    if not capability_ok:
        user = await _authenticated_user(request, db)
        if not user or not await _user_owns_file(db, user, filename):
            raise NOT_FOUND
        if org:
            organization = (await db.execute(select(Organization).where(Organization.id == org))).scalar_one_or_none()
            if organization is not None and (organization.status or "active") != "active":
                raise NOT_FOUND

    media_type, headers = media_response_headers(filename)
    return FileResponse(file_path, media_type=media_type, headers=headers)
