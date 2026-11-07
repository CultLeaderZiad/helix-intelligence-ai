"""Saved Discover search drafts: list, save and delete, per user per workspace."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search_draft import SearchDraft
from app.models.user import User

MAX_DRAFTS_PER_USER = 50
# Only the filters the results view understands are kept.
_FILTER_KEYS = {"country", "min_days_active", "min_score"}


async def _active_org(db: AsyncSession, user: User) -> str:
    from app.services.billing_service import resolve_active_org

    org = await resolve_active_org(db, user)
    if org is None:
        raise HTTPException(status_code=404, detail="No workspace found")
    return org.id


def _clean_filters(filters: Optional[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in (filters or {}).items():
        if key not in _FILTER_KEYS:
            continue
        if key == "country" and isinstance(value, str) and len(value) <= 8:
            out[key] = value
        elif key in {"min_days_active", "min_score"} and isinstance(value, (int, float)) and 0 <= value <= 365:
            out[key] = value
    return out


def _view(draft: SearchDraft) -> dict[str, Any]:
    return {
        "id": draft.id,
        "title": draft.title,
        "query": draft.query,
        "notes": draft.notes or "",
        "filters": draft.filters or {},
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
    }


async def list_drafts(db: AsyncSession, user: User) -> list[dict[str, Any]]:
    org_id = await _active_org(db, user)
    rows = (await db.execute(
        select(SearchDraft)
        .where(SearchDraft.org_id == org_id, SearchDraft.user_id == user.id)
        .order_by(SearchDraft.created_at.desc(), SearchDraft.id)
        .limit(MAX_DRAFTS_PER_USER)
    )).scalars().all()
    return [_view(d) for d in rows]


async def save_draft(
    db: AsyncSession, user: User, *, title: str, query: str, notes: str = "", filters: Optional[dict] = None
) -> dict[str, Any]:
    query = (query or "").strip()
    title = (title or "").strip() or query
    if not query:
        raise HTTPException(status_code=422, detail={"code": "empty_query", "message": "A draft needs a search query."})
    org_id = await _active_org(db, user)
    count = await db.scalar(select(func.count(SearchDraft.id)).where(
        SearchDraft.org_id == org_id, SearchDraft.user_id == user.id
    )) or 0
    if count >= MAX_DRAFTS_PER_USER:
        raise HTTPException(status_code=409, detail={
            "code": "too_many_drafts", "message": f"Delete a draft first (limit {MAX_DRAFTS_PER_USER}).",
        })
    draft = SearchDraft(
        org_id=org_id,
        user_id=user.id,
        title=title[:200],
        query=query[:500],
        notes=(notes or "").strip()[:2000],
        filters=_clean_filters(filters),
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)
    return _view(draft)


async def delete_draft(db: AsyncSession, user: User, draft_id: str) -> dict[str, Any]:
    org_id = await _active_org(db, user)
    draft = (await db.execute(select(SearchDraft).where(
        SearchDraft.id == draft_id, SearchDraft.org_id == org_id, SearchDraft.user_id == user.id
    ))).scalar_one_or_none()
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    await db.delete(draft)
    await db.commit()
    return {"deleted": draft_id}
