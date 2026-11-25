"""Ask Helix saved conversations: list, open, rename, pin, archive, delete, and the memory the model sees.

Private to the user who had them (the query filters by user and workspace, and RLS enforces
both). Nothing is deleted on its own: past MAX_ACTIVE per user the oldest unpinned
conversation is archived (still readable and restorable). The model sees only the last few
turns, trimmed, so cost and context stay bounded.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_conversation import AgentConversation, AgentMessage
from app.models.user import User

MAX_ACTIVE = 50
_TABLES = ("agent_conversations", "agent_messages")


def tables_missing(exc: BaseException) -> bool:
    """True when the history tables are not in the database yet (the migration has not been applied).

    Ask Helix keeps answering without saving until then, instead of failing every question."""
    text = str(getattr(exc, "orig", exc)).lower()
    return any(t in text for t in _TABLES) and ("does not exist" in text or "undefinedtable" in text)

MAX_ARCHIVED_LISTED = 100
MAX_MESSAGES = 200
MEMORY_TURNS = 6
MEMORY_CHARS = 500
_PAYLOAD_KEYS = ("citations", "proposals", "tools_used", "model", "assistant", "effort",
                 "references_used", "references_missing", "label")


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def title_from(question: str) -> str:
    one_line = " ".join((question or "").split())
    return (one_line[:60] + "…") if len(one_line) > 60 else (one_line or "New chat")


def _view(c: AgentConversation) -> Dict[str, Any]:
    return {
        "id": c.id, "title": c.title, "pinned": bool(c.pinned),
        "archived": c.archived_at is not None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def message_view(m: AgentMessage) -> Dict[str, Any]:
    out = {"id": m.id, "role": m.role, "content": m.content,
           "created_at": m.created_at.isoformat() if m.created_at else None}
    if m.role == "assistant":
        out.update(m.payload or {})
    return out


async def _own(db: AsyncSession, user: User, org_id: str, conversation_id: str) -> AgentConversation:
    row = (await db.execute(select(AgentConversation).where(
        AgentConversation.id == conversation_id, AgentConversation.org_id == org_id,
        AgentConversation.user_id == user.id,
    ))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return row


async def list_conversations(db: AsyncSession, user: User, org_id: str, archived: bool = False) -> List[Dict[str, Any]]:
    q = select(AgentConversation).where(AgentConversation.org_id == org_id, AgentConversation.user_id == user.id)
    q = q.where(AgentConversation.archived_at.is_not(None) if archived else AgentConversation.archived_at.is_(None))
    q = q.order_by(AgentConversation.pinned.desc(), AgentConversation.updated_at.desc(), AgentConversation.id)
    rows = (await db.execute(q.limit(MAX_ARCHIVED_LISTED if archived else MAX_ACTIVE + 1))).scalars().all()
    return [_view(c) for c in rows]


async def get_conversation(db: AsyncSession, user: User, org_id: str, conversation_id: str) -> Dict[str, Any]:
    c = await _own(db, user, org_id, conversation_id)
    msgs = (await db.execute(select(AgentMessage).where(AgentMessage.conversation_id == c.id)
                             .order_by(AgentMessage.created_at, AgentMessage.id).limit(MAX_MESSAGES))).scalars().all()
    return {**_view(c), "messages": [message_view(m) for m in msgs]}


async def update_conversation(db: AsyncSession, user: User, org_id: str, conversation_id: str, *,
                              title: Optional[str] = None, pinned: Optional[bool] = None,
                              archived: Optional[bool] = None) -> Dict[str, Any]:
    c = await _own(db, user, org_id, conversation_id)
    if title is not None:
        clean = " ".join(title.split())[:200]
        if not clean:
            raise HTTPException(status_code=422, detail={"code": "empty_title", "message": "A title is required."})
        c.title = clean
    if pinned is not None:
        c.pinned = pinned
    if archived is not None:
        if archived:
            c.archived_at = _now()
            c.pinned = False
        elif c.archived_at is not None:
            c.archived_at = None
            await db.flush()
            await _make_room(db, user, org_id, keep=c.id)
    await db.commit()
    await db.refresh(c)
    return _view(c)


async def delete_conversation(db: AsyncSession, user: User, org_id: str, conversation_id: str) -> Dict[str, Any]:
    c = await _own(db, user, org_id, conversation_id)
    await db.delete(c)  # messages go with it (ON DELETE CASCADE)
    await db.commit()
    return {"deleted": conversation_id}


async def _make_room(db: AsyncSession, user: User, org_id: str, keep: Optional[str] = None) -> int:
    """Archive the oldest unpinned conversations so that, counting `keep` (or one new one), at most MAX_ACTIVE stay active."""
    active = (await db.execute(select(AgentConversation).where(
        AgentConversation.org_id == org_id, AgentConversation.user_id == user.id,
        AgentConversation.archived_at.is_(None),
    ).order_by(AgentConversation.updated_at.asc(), AgentConversation.id))).scalars().all()
    others = [c for c in active if c.id != keep]
    excess = len(others) + 1 - MAX_ACTIVE  # +1: the conversation being created or restored
    archived = 0
    for c in others:
        if excess <= 0:
            break
        if c.pinned:
            continue
        c.archived_at = _now()
        excess -= 1
        archived += 1
    if excess > 0:
        raise HTTPException(status_code=409, detail={
            "code": "too_many_pinned",
            "message": f"You have {MAX_ACTIVE} pinned conversations. Unpin or delete one first.",
        })
    return archived


async def history_for_model(db: AsyncSession, user: User, org_id: str, conversation_id: str) -> List[Dict[str, str]]:
    """The last few turns of this conversation, trimmed. Checks ownership."""
    c = await _own(db, user, org_id, conversation_id)
    count = await db.scalar(select(func.count(AgentMessage.id)).where(AgentMessage.conversation_id == c.id)) or 0
    if count + 2 > MAX_MESSAGES:  # refuse before the question is spent on the model
        raise HTTPException(status_code=409, detail={
            "code": "conversation_full",
            "message": "This conversation is long. Start a new one to keep going.",
        })
    rows = (await db.execute(select(AgentMessage).where(AgentMessage.conversation_id == c.id)
                             .order_by(AgentMessage.created_at.desc(), AgentMessage.id.desc())
                             .limit(MEMORY_TURNS))).scalars().all()
    return [{"role": m.role, "content": (m.content or "")[:MEMORY_CHARS]} for m in reversed(rows)]


async def record_turn(db: AsyncSession, user: User, org_id: str, conversation_id: Optional[str],
                      question: str, result: Dict[str, Any]) -> str:
    """Save the question and the answer; start a conversation when none is given. Returns its id."""
    if conversation_id:
        c = await _own(db, user, org_id, conversation_id)
        if c.archived_at is not None:  # continuing an archived chat brings it back
            c.archived_at = None
            await db.flush()
            await _make_room(db, user, org_id, keep=c.id)
        count =await db.scalar(select(func.count(AgentMessage.id)).where(AgentMessage.conversation_id == c.id)) or 0
        if count + 2 > MAX_MESSAGES:
            raise HTTPException(status_code=409, detail={
                "code": "conversation_full",
                "message": "This conversation is long. Start a new one to keep going.",
            })
    else:
        await _make_room(db, user, org_id)
        c = AgentConversation(org_id=org_id, user_id=user.id, title=title_from(question))
        db.add(c)
        await db.flush()
    t = _now()
    db.add(AgentMessage(conversation_id=c.id, org_id=org_id, user_id=user.id, role="user",
                        content=question.strip()[:2000], created_at=t))
    payload = {k: result.get(k) for k in _PAYLOAD_KEYS if k in result}
    db.add(AgentMessage(conversation_id=c.id, org_id=org_id, user_id=user.id, role="assistant",
                        content=str(result.get("answer") or "")[:8000], payload=payload,
                        created_at=t + datetime.timedelta(milliseconds=1)))
    await db.execute(update(AgentConversation).where(AgentConversation.id == c.id).values(updated_at=t))
    await db.commit()
    return c.id
