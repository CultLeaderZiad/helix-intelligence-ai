"""Guest board links: signed, read-only, revocable, expiring.

Token format: ``<payload>.<mac>`` where ``payload`` is base64url JSON
``{"l": link_id, "o": org_id, "e": expires_unix}`` and ``mac`` is
HMAC-SHA256 over the payload with a key derived from SECRET_KEY for this
purpose only. The guest read:

1. checks the MAC (constant time) and the expiry before touching the
   database, so forged or expired tokens cost nothing;
2. binds RLS to exactly the token's workspace (no user, no admin bypass);
3. requires the link row to exist in that workspace, unrevoked, with the
   same expiry the token carries;
4. returns only display fields of that board's saved ads.

Every failure is the same 404, so a link cannot be probed.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.tenancy import tenant_db_scope
from app.models.board_share_link import BoardShareLink
from app.models.creative import Creative
from app.models.creative_score import CreativeScore
from app.models.saved_creative import SavedCreative
from app.models.user import User

EXPIRY_CHOICES_DAYS = (1, 7, 30)
MAX_ACTIVE_LINKS_PER_BOARD = 5
GUEST_PAGE_LIMIT = 100
NOT_FOUND = HTTPException(status_code=404, detail="This board link is not available.")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _key() -> bytes:
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY is required to sign board links")
    return hashlib.sha256(b"helix-board-share-v1|" + settings.SECRET_KEY.encode("utf-8")).digest()


def _mac(payload: str) -> str:
    return _b64(hmac.new(_key(), payload.encode("ascii"), hashlib.sha256).digest())


def sign_token(link_id: str, org_id: str, expires_at: datetime) -> str:
    payload = _b64(json.dumps(
        {"l": link_id, "o": org_id, "e": int(expires_at.timestamp())}, separators=(",", ":")
    ).encode("utf-8"))
    return f"{payload}.{_mac(payload)}"


def verify_token(token: str, *, now: Optional[datetime] = None) -> Optional[dict]:
    """Return the payload when the MAC is valid and unexpired; otherwise None."""
    if not token or len(token) > 512 or token.count(".") != 1:
        return None
    payload, mac = token.split(".")
    try:
        if not hmac.compare_digest(_mac(payload), mac):
            return None
        data = json.loads(_unb64(payload))
        link_id, org_id, exp = str(data["l"]), str(data["o"]), int(data["e"])
    except (ValueError, KeyError, TypeError):
        return None
    current = (now or datetime.now(timezone.utc)).timestamp()
    if exp <= current or not link_id or not org_id:
        return None
    return {"link_id": link_id, "org_id": org_id, "exp": exp}


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _link_view(link: BoardShareLink) -> dict:
    expires_at = _aware(link.expires_at)
    now = datetime.now(timezone.utc)
    state = "revoked" if link.revoked_at else ("expired" if expires_at <= now else "active")
    view = {
        "id": link.id,
        "collection": link.collection_name,
        "expires_at": expires_at.isoformat(),
        "revoked_at": _aware(link.revoked_at).isoformat() if link.revoked_at else None,
        "created_at": _aware(link.created_at).isoformat() if link.created_at else None,
        "state": state,
        "url": None,
    }
    if state == "active":
        view["url"] = f"/b/{sign_token(link.id, link.org_id, expires_at)}"
    return view


async def _owner_org(db: AsyncSession, user: User) -> str:
    """The same workspace that saving an ad uses (and that require_feature checked)."""
    from app.services.billing_service import resolve_active_org

    org = await resolve_active_org(db, user)
    if org is None:
        raise HTTPException(status_code=404, detail="No workspace found")
    return org.id


async def create_link(db: AsyncSession, user: User, collection: str, expires_in_days: int) -> dict:
    collection = (collection or "").strip()
    if not collection or len(collection) > 200:
        raise HTTPException(status_code=422, detail={"code": "invalid_board", "message": "Choose a board to share."})
    if expires_in_days not in EXPIRY_CHOICES_DAYS:
        raise HTTPException(status_code=422, detail={
            "code": "invalid_expiry", "message": f"Expiry must be one of {list(EXPIRY_CHOICES_DAYS)} days.",
        })
    org_id = await _owner_org(db, user)
    saved = await db.scalar(select(func.count(SavedCreative.id)).where(
        SavedCreative.user_id == user.id,
        SavedCreative.org_id == org_id,
        SavedCreative.collection_name == collection,
    )) or 0
    if saved == 0:
        raise HTTPException(status_code=404, detail="Board not found")
    now = datetime.now(timezone.utc)
    active = await db.scalar(select(func.count(BoardShareLink.id)).where(
        BoardShareLink.org_id == org_id,
        BoardShareLink.created_by == user.id,
        BoardShareLink.collection_name == collection,
        BoardShareLink.revoked_at.is_(None),
        BoardShareLink.expires_at > now,
    )) or 0
    if active >= MAX_ACTIVE_LINKS_PER_BOARD:
        raise HTTPException(status_code=409, detail={
            "code": "too_many_links", "message": "Revoke an existing link for this board first.",
        })
    link = BoardShareLink(
        org_id=org_id,
        created_by=user.id,
        collection_name=collection,
        # Whole seconds, so the expiry in the token equals the stored one.
        expires_at=(now + timedelta(days=expires_in_days)).replace(microsecond=0),
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return _link_view(link)


async def list_boards(db: AsyncSession, user: User) -> list[dict]:
    """The caller's boards (saved-ad collections) in their workspace, with counts."""
    org_id = await _owner_org(db, user)
    rows = (await db.execute(
        select(SavedCreative.collection_name, func.count(SavedCreative.id))
        .where(SavedCreative.user_id == user.id, SavedCreative.org_id == org_id)
        .group_by(SavedCreative.collection_name)
        .order_by(SavedCreative.collection_name)
    )).all()
    return [{"name": name, "count": count} for name, count in rows]


async def list_links(db: AsyncSession, user: User, collection: Optional[str] = None) -> list[dict]:
    org_id = await _owner_org(db, user)
    query = select(BoardShareLink).where(
        BoardShareLink.org_id == org_id, BoardShareLink.created_by == user.id
    )
    if collection:
        query = query.where(BoardShareLink.collection_name == collection)
    rows = (await db.execute(query.order_by(BoardShareLink.created_at.desc()).limit(100))).scalars().all()
    return [_link_view(link) for link in rows]


async def revoke_link(db: AsyncSession, user: User, link_id: str) -> dict:
    org_id = await _owner_org(db, user)
    link = (await db.execute(select(BoardShareLink).where(
        BoardShareLink.id == link_id,
        BoardShareLink.org_id == org_id,
        BoardShareLink.created_by == user.id,
    ))).scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    if link.revoked_at is None:
        link.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(link)
    return _link_view(link)


def _guest_item(c: Creative, score: Optional[CreativeScore]) -> dict:
    from app.services.storage_service import resolve_stored_url

    def media(url):
        try:
            return resolve_stored_url(url)
        except RuntimeError:
            return None

    official = (c.data_source or "unknown") == "meta_official"
    return {
        "id": c.id,
        "brand_name": c.brand_name,
        "platform": c.platform,
        "format": c.format,
        "headline": c.headline or "",
        "body": c.body or "",
        "cta": c.cta or "",
        "landing_domain": c.landing_domain,
        "media_url": media(c.media_url),
        "thumbnail_url": media(c.thumbnail_url),
        "first_seen": c.first_seen,
        "last_seen": c.last_seen,
        "days_active": c.days_active,
        "text_rubric_score": score.composite if score else None,
        "impressions_est": c.impressions_est if official else None,
        "permalink": c.permalink,
    }


async def read_guest_board(db: AsyncSession, token: str) -> dict:
    claims = verify_token(token)
    if claims is None:
        raise NOT_FOUND
    # Bind RLS to the token's workspace only: no user id, no admin bypass.
    async with tenant_db_scope(db, [claims["org_id"]], ""):
        link = (await db.execute(select(BoardShareLink).where(
            BoardShareLink.id == claims["link_id"],
            BoardShareLink.org_id == claims["org_id"],
        ))).scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if (
            link is None
            or link.revoked_at is not None
            or _aware(link.expires_at) <= now
            or int(_aware(link.expires_at).timestamp()) != claims["exp"]
        ):
            raise NOT_FOUND
        # A suspended or banned creator's links stop working at once, like
        # their sessions do; revocation/expiry alone left them readable.
        async with tenant_db_scope(db, [claims["org_id"]], str(link.created_by or "")):
            creator = (await db.execute(
                select(User.is_suspended, User.is_banned).where(User.id == link.created_by)
            )).first()
        if creator is None or creator.is_suspended or creator.is_banned:
            raise NOT_FOUND
        rows = (await db.execute(
            select(Creative, CreativeScore)
            .join(SavedCreative, SavedCreative.creative_id == Creative.id)
            .outerjoin(CreativeScore, CreativeScore.creative_id == Creative.id)
            .where(
                SavedCreative.org_id == link.org_id,
                SavedCreative.user_id == link.created_by,
                SavedCreative.collection_name == link.collection_name,
            )
            .order_by(SavedCreative.created_at.desc(), SavedCreative.id)
            .limit(GUEST_PAGE_LIMIT)
        )).all()
        items = [_guest_item(c, score) for c, score in rows]
        board = {
            "board": link.collection_name,
            "expires_at": _aware(link.expires_at).isoformat(),
            "read_only": True,
            "items": items,
            "total": len(items),
        }
    await db.rollback()
    return board
