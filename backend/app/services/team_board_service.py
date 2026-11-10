"""Team boards: every current member of a workspace can read the workspace's boards.

Only when the workspace is granted ``team_accounts`` (the router enforces
it). Read-only: saving, removing and sharing stay with each board's owner.
A board of someone who has left the workspace is not shown.
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select, union
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.creative import Creative
from app.models.creative_score import CreativeScore
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.saved_creative import SavedCreative
from app.models.user import User

TEAM_PAGE_LIMIT = 100


async def _active_org_id(db: AsyncSession, user: User) -> str:
    from app.services.billing_service import resolve_active_org

    org = await resolve_active_org(db, user)
    if org is None:
        raise HTTPException(status_code=404, detail="No workspace found")
    return org.id


def _current_people(org_id: str):
    owner = select(Organization.owner_id.label("user_id")).where(Organization.id == org_id)
    members = select(OrganizationMember.user_id.label("user_id")).where(OrganizationMember.org_id == org_id)
    return union(owner, members).subquery()


def _display_name(user: User) -> str:
    if user.full_name:
        return user.full_name
    return (user.email or "").split("@", 1)[0] or "Member"


async def list_team_boards(db: AsyncSession, user: User) -> list[dict]:
    org_id = await _active_org_id(db, user)
    people = _current_people(org_id)
    rows = (await db.execute(
        select(SavedCreative.user_id, SavedCreative.collection_name, func.count(SavedCreative.id), User)
        .join(people, people.c.user_id == SavedCreative.user_id)
        .join(User, User.id == SavedCreative.user_id)
        .where(SavedCreative.org_id == org_id)
        .group_by(SavedCreative.user_id, SavedCreative.collection_name, User.id)
        .order_by(SavedCreative.collection_name, SavedCreative.user_id)
    )).all()
    return [
        {
            "owner_id": owner_id,
            "owner_name": _display_name(owner),
            "is_mine": owner_id == user.id,
            "name": name,
            "count": count,
        }
        for owner_id, name, count, owner in rows
    ]


async def get_team_board(db: AsyncSession, user: User, owner_id: str, collection: str) -> dict:
    from app.services.board_share_service import _guest_item

    org_id = await _active_org_id(db, user)
    people = _current_people(org_id)
    is_current = await db.scalar(select(func.count()).select_from(people).where(people.c.user_id == owner_id))
    if not is_current:
        raise HTTPException(status_code=404, detail="Board not found")
    rows = (await db.execute(
        select(Creative, CreativeScore)
        .join(SavedCreative, SavedCreative.creative_id == Creative.id)
        .outerjoin(CreativeScore, CreativeScore.creative_id == Creative.id)
        .where(
            SavedCreative.org_id == org_id,
            SavedCreative.user_id == owner_id,
            SavedCreative.collection_name == collection,
        )
        .order_by(SavedCreative.created_at.desc(), SavedCreative.id)
        .limit(TEAM_PAGE_LIMIT)
    )).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Board not found")
    owner: Optional[User] = (await db.execute(select(User).where(User.id == owner_id))).scalar_one_or_none()
    return {
        "board": collection,
        "owner_name": _display_name(owner) if owner else "Member",
        "read_only": owner_id != user.id,
        "items": [_guest_item(c, s) for c, s in rows],
    }
