"""W9 review: stored results and the brand-monitor preview stay in the
caller's workspace. Tags, notes and archive search have their own
cross-workspace tests (test_w9_2_tags_notes_monitor, test_w9_archive_search)."""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.routers import discover
from app.db.session import async_session_maker
from app.models.monitor import Monitor
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.services import monitor_service


async def _workspace(db, suffix):
    user = User(id=f"u_{suffix}", email=f"w9t-{suffix}@example.com", password_hash="x", role="member")
    db.add(user)
    await db.flush()
    org = Organization(id=f"o_{suffix}", name="W9T", owner_id=user.id, plan="pro")
    db.add(org)
    await db.flush()
    return user, org


def _request():
    return Request({"type": "http", "method": "GET", "path": "/api/discovery/stored-results",
                    "query_string": b"", "headers": []})


@pytest.mark.asyncio
async def test_stored_results_never_return_another_workspaces_search():
    suffix = uuid.uuid4().hex[:8]
    query = f"acme-{suffix}"
    async with async_session_maker() as db:
        _owner, org = await _workspace(db, suffix)
        stranger, _other = await _workspace(db, suffix + "x")
        db.add(ScrapeJob(id=f"j_{suffix}", org_id=org.id, query=query, status="succeeded"))
        await db.commit()

        with pytest.raises(HTTPException) as missing:
            await discover.stored_results(query=query, request=_request(), db=db, current_user=stranger)
        assert missing.value.status_code == 404


@pytest.mark.asyncio
async def test_brand_monitor_preview_ignores_another_workspaces_monitor():
    suffix = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        owner, org = await _workspace(db, suffix)
        _stranger, other = await _workspace(db, suffix + "x")
        db.add(Monitor(org_id=org.id, user_id=owner.id, name="Gymshark", query="123456789", filters={},
                       cadence="weekly", status="active"))
        await db.commit()

        mine = await monitor_service.brand_monitor_preview(db, org_id=org.id, page_id="123456789", brand_name=None)
        theirs = await monitor_service.brand_monitor_preview(db, org_id=other.id, page_id="123456789", brand_name=None)
        assert mine["existing_monitor_id"]
        assert theirs["existing_monitor_id"] is None
