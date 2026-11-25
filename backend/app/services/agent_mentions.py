"""@ mentions for Ask Helix: what a user can point at, and how a mention becomes context.

A user types "@" in the prompt box and picks something from their own workspace:
- ``search``  a search they ran in Discover (its stored results, 0 records spent);
- ``draft``   a saved search draft (title, query, notes and filters);
- ``board``   a board of saved ads (no notes);
- ``monitor`` a monitor with its recent events;
- ``ad``      one ad.

Everything is read from the caller's own workspace and nothing is searched or
spent. A mention is resolved on the server from its type and id; the browser
never sends content. Resolved text reaches the model as data inside
<reference> tags, never as instructions. A draft's notes are included only
because the user chose to mention that draft. An id that is not in the
caller's workspace is reported back as missing and adds nothing to the prompt.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitor import Monitor
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.services import agent_service, board_share_service, monitor_service, search_draft_service
from app.services.text_search import normalize_arabic

REF_TYPES = ("search", "draft", "board", "monitor", "ad")
MAX_REFS = 5
PER_TYPE = 8
RESULT_CHARS = 5000


def _fold(text: str) -> str:
    return normalize_arabic((text or "").lower()).strip()


def _label(text: str) -> str:
    return " ".join(str(text or "").replace('"', "'").replace("<", "‹").replace(">", "›").split())[:120]


async def candidates(db: AsyncSession, user: User, org_id: str, scope: Optional[list],
                     q: str = "", limit: int = 20) -> List[Dict[str, str]]:
    """What the "@" menu offers for ``q``: the user's own searches, drafts, boards and monitors."""
    needle = _fold(q)

    def match(*texts: str) -> bool:
        return not needle or any(needle in _fold(t) for t in texts)

    out: List[Dict[str, str]] = []

    stmt = select(ScrapeJob.query, ScrapeJob.created_at, ScrapeJob.record_count).where(ScrapeJob.status == "succeeded")
    if scope is not None:
        stmt = stmt.where(ScrapeJob.org_id.in_(scope or [""]))
    seen: set = set()
    found = 0
    for query, created_at, count in (await db.execute(stmt.order_by(ScrapeJob.created_at.desc()).limit(200))).all():
        key = " ".join((query or "").split()).lower()
        if not key or key in seen or not match(query):
            continue
        seen.add(key)
        day = created_at.date().isoformat() if created_at else ""
        out.append({"type": "search", "id": " ".join(query.split()), "label": _label(query),
                    "hint": f"Search · {count} ads · {day}" if count else f"Search · {day}"})
        found += 1
        if found >= PER_TYPE:
            break

    for draft in (await search_draft_service.list_drafts(db, user))[:100]:
        if match(draft["title"], draft["query"]) and sum(1 for o in out if o["type"] == "draft") < PER_TYPE:
            out.append({"type": "draft", "id": draft["id"], "label": _label(draft["title"]), "hint": f"Draft · {_label(draft['query'])}"})

    for board in await board_share_service.list_boards(db, user):
        if match(board["name"]) and sum(1 for o in out if o["type"] == "board") < PER_TYPE:
            out.append({"type": "board", "id": board["name"], "label": _label(board["name"]), "hint": f"Board · {board['count']} ads"})

    monitors = (await db.execute(
        select(Monitor).where(Monitor.org_id == org_id).order_by(Monitor.created_at.desc()).limit(50)
    )).scalars().all()
    for monitor in monitors:
        if match(monitor.name, monitor.query) and sum(1 for o in out if o["type"] == "monitor") < PER_TYPE:
            out.append({"type": "monitor", "id": monitor.id, "label": _label(monitor.name),
                        "hint": f"Monitor · {monitor.cadence} · {monitor.status}"})
    return out[: max(1, min(int(limit), 40))]


async def _payload(ctx: "agent_service.AgentContext", ref_type: str, ref_id: str) -> Optional[Tuple[str, Any]]:
    """(label, data) for one mention, or None when it is not in the caller's workspace."""
    try:
        if ref_type == "search":
            data = await agent_service.t_get_stored_results(ctx, {"query": ref_id})
            return (_label(ref_id), None) if "error" in data else (_label(ref_id), data)
        if ref_type == "board":
            data = await agent_service.t_get_board(ctx, {"collection": ref_id})
            return _label(ref_id), data
        if ref_type == "ad":
            data = await agent_service.t_get_ad(ctx, {"creative_id": ref_id})
            return _label(data["ad"].get("headline") or ref_id), data
        if ref_type == "draft":
            for draft in await search_draft_service.list_drafts(ctx.db, ctx.user):
                if draft["id"] == ref_id:
                    return _label(draft["title"]), {k: draft[k] for k in ("title", "query", "notes", "filters")}
            return None
        if ref_type == "monitor":
            monitor = (await ctx.db.execute(
                select(Monitor).where(Monitor.id == ref_id, Monitor.org_id == ctx.org_id)
            )).scalar_one_or_none()
            if monitor is None:
                return None
            events = await monitor_service.get_monitor_events(ctx.db, ctx.org_id, monitor_id=monitor.id, limit=10)
            return _label(monitor.name), {"name": monitor.name, "query": monitor.query, "cadence": monitor.cadence,
                                          "status": monitor.status, "recent_events": events}
    except (HTTPException, ValueError):
        return None
    return None


async def resolve(ctx: "agent_service.AgentContext", refs: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, str]], List[Dict[str, str]]]:
    """(prompt blocks, used, missing) for the mentions of one question."""
    blocks: List[str] = []
    used: List[Dict[str, str]] = []
    missing: List[Dict[str, str]] = []
    seen: set = set()
    for ref in (refs or [])[: MAX_REFS + 5]:
        ref_type, ref_id = str(ref.get("type") or ""), str(ref.get("id") or "").strip()
        if ref_type not in REF_TYPES or not (1 <= len(ref_id) <= 200) or (ref_type, ref_id) in seen:
            continue
        seen.add((ref_type, ref_id))
        if len(used) >= MAX_REFS:
            break
        resolved = await _payload(ctx, ref_type, ref_id)
        if resolved is None or resolved[1] is None:
            missing.append({"type": ref_type, "id": ref_id})
            continue
        label, data = resolved
        text = json.dumps(data, ensure_ascii=False, default=str)[:RESULT_CHARS]
        blocks.append(f'<reference type="{ref_type}" label="{label}">\n{text}\n</reference>')
        used.append({"type": ref_type, "id": ref_id, "label": label})
    return blocks, used, missing
