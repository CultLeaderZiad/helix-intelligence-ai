"""W9-2: tags and notes on the caller's saved ads. 0 credits, 0 records.

A saved ad is one ``saved_creatives`` row, addressed by its creative id like
the save/unsave endpoints. Only the user who saved it can tag it or add notes;
only a note's author can edit or delete that note. Every row carries the
saved ad's ``org_id`` so tenant RLS keeps it inside the workspace.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.saved_ad_annotation import SavedAdNote, SavedAdTag
from app.models.saved_creative import SavedCreative
from app.services import text_search

MAX_TAG_LENGTH = 40
MAX_TAGS_PER_AD = 20
MAX_NOTE_LENGTH = 2000
MAX_NOTES_PER_AD = 50


def clean_tag(raw: str) -> str:
    return " ".join(str(raw or "").split()).lower()[:MAX_TAG_LENGTH]


def clean_tags(raw: Iterable[str]) -> list[str]:
    out: list[str] = []
    for value in raw or []:
        tag = clean_tag(value)
        if tag and tag not in out:
            out.append(tag)
    if len(out) > MAX_TAGS_PER_AD:
        raise HTTPException(
            status_code=422,
            detail={"code": "too_many_tags", "message": f"A saved ad can have up to {MAX_TAGS_PER_AD} tags."},
        )
    return out


def clean_note(raw: str) -> str:
    body = (raw or "").strip()
    if not body:
        raise HTTPException(status_code=422, detail={"code": "empty_note", "message": "A note needs some text."})
    if len(body) > MAX_NOTE_LENGTH:
        raise HTTPException(
            status_code=422,
            detail={"code": "note_too_long", "message": f"Notes are limited to {MAX_NOTE_LENGTH} characters."},
        )
    return body


async def _require_feature(db: AsyncSession, user) -> None:
    from app.services.billing_service import check_quota_and_feature

    await check_quota_and_feature(db, user, feature_name="swipe_files", required_credits=0.0)


async def _saved(db: AsyncSession, user, creative_id: str) -> SavedCreative:
    row = (await db.execute(
        select(SavedCreative).where(SavedCreative.user_id == user.id, SavedCreative.creative_id == creative_id)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "not_saved", "message": "Save this ad to a board first."})
    return row


def note_view(note: SavedAdNote) -> dict:
    return {
        "id": note.id,
        "body": note.body,
        "author_id": note.author_id,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    }


async def annotations_for(db: AsyncSession, saved_ids: list[str]) -> dict[str, dict]:
    """Tags and notes for many saved rows in two queries."""
    out = {sid: {"tags": [], "notes": []} for sid in saved_ids}
    if not saved_ids:
        return out
    tags = (await db.execute(
        select(SavedAdTag.saved_creative_id, SavedAdTag.tag)
        .where(SavedAdTag.saved_creative_id.in_(saved_ids))
        .order_by(SavedAdTag.tag)
    )).all()
    for sid, tag in tags:
        out[sid]["tags"].append(tag)
    notes = (await db.execute(
        select(SavedAdNote)
        .where(SavedAdNote.saved_creative_id.in_(saved_ids))
        .order_by(SavedAdNote.created_at, SavedAdNote.id)
    )).scalars().all()
    for note in notes:
        out[note.saved_creative_id]["notes"].append(note_view(note))
    return out


async def set_tags(db: AsyncSession, user, creative_id: str, tags: Iterable[str]) -> dict:
    await _require_feature(db, user)
    saved = await _saved(db, user, creative_id)
    wanted = clean_tags(tags)
    current = set((await db.execute(
        select(SavedAdTag.tag).where(SavedAdTag.saved_creative_id == saved.id)
    )).scalars().all())
    removed = current - set(wanted)
    if removed:
        await db.execute(delete(SavedAdTag).where(SavedAdTag.saved_creative_id == saved.id, SavedAdTag.tag.in_(removed)))
    for tag in wanted:
        if tag not in current:
            db.add(SavedAdTag(org_id=saved.org_id, saved_creative_id=saved.id, tag=tag, created_by=user.id))
    await db.commit()
    return {"creative_id": creative_id, "tags": sorted(wanted)}


async def list_tags(db: AsyncSession, user) -> list[dict]:
    """The caller's tags with how many of their saved ads carry each."""
    await _require_feature(db, user)
    rows = (await db.execute(
        select(SavedAdTag.tag, func.count(SavedAdTag.id))
        .join(SavedCreative, SavedCreative.id == SavedAdTag.saved_creative_id)
        .where(SavedCreative.user_id == user.id)
        .group_by(SavedAdTag.tag)
        .order_by(func.count(SavedAdTag.id).desc(), SavedAdTag.tag)
        .limit(200)
    )).all()
    return [{"tag": tag, "count": int(count)} for tag, count in rows]


async def add_note(db: AsyncSession, user, creative_id: str, body: str) -> dict:
    await _require_feature(db, user)
    saved = await _saved(db, user, creative_id)
    body = clean_note(body)
    count = await db.scalar(select(func.count(SavedAdNote.id)).where(SavedAdNote.saved_creative_id == saved.id)) or 0
    if count >= MAX_NOTES_PER_AD:
        raise HTTPException(
            status_code=422,
            detail={"code": "too_many_notes", "message": f"A saved ad can have up to {MAX_NOTES_PER_AD} notes."},
        )
    note = SavedAdNote(org_id=saved.org_id, saved_creative_id=saved.id, author_id=user.id, body=body)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note_view(note)


async def _own_note(db: AsyncSession, user, creative_id: str, note_id: str) -> SavedAdNote:
    saved = await _saved(db, user, creative_id)
    note = (await db.execute(
        select(SavedAdNote).where(SavedAdNote.id == note_id, SavedAdNote.saved_creative_id == saved.id)
    )).scalar_one_or_none()
    if note is None or note.author_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "note_not_found", "message": "Note not found."})
    return note


async def update_note(db: AsyncSession, user, creative_id: str, note_id: str, body: str) -> dict:
    await _require_feature(db, user)
    note = await _own_note(db, user, creative_id, note_id)
    note.body = clean_note(body)
    note.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(note)
    return note_view(note)


async def delete_note(db: AsyncSession, user, creative_id: str, note_id: str) -> dict:
    await _require_feature(db, user)
    note = await _own_note(db, user, creative_id, note_id)
    await db.delete(note)
    await db.commit()
    return {"deleted": True, "id": note_id}


# --- filters used by the saved-ads list and archive search -----------------

NOTE_DOC = (
    "(to_tsvector('simple'::regconfig, saved_ad_notes.body) || "
    "to_tsvector('arabic'::regconfig, saved_ad_notes.body))"
)


def has_tag(tag: str):
    return select(SavedAdTag.id).where(
        SavedAdTag.saved_creative_id == SavedCreative.id, SavedAdTag.tag == clean_tag(tag)
    ).exists()


def tag_or_note_matches(needle: str):
    """A saved ad whose tag equals the query, or whose notes match it (FTS)."""
    tag_hit = has_tag(needle)
    note_hit = select(SavedAdNote.id).where(
        SavedAdNote.saved_creative_id == SavedCreative.id,
        text(f"{NOTE_DOC} @@ {text_search.QUERY_SQL}").bindparams(fts_q=needle),
    ).exists()
    return or_(tag_hit, note_hit)
