"""W8: a search's workspace lock does not wait on an open archive insert.

Found in the Discover proof: POST /discovery/jobs returned 500 (TimeoutError)
while the worker archived media. The archive transaction had inserted an
ad_archive row (the FK takes FOR KEY SHARE on the workspace row) and stayed
open during downloads; the search's FOR UPDATE on the same row waited past the
30 s command timeout. Workspace locks are now FOR NO KEY UPDATE.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from app.db.session import async_session_maker, engine
from app.models.organization import Organization
from app.models.user import User


async def _workspace(s: str) -> str:
    async with async_session_maker() as db:
        db.add(User(id=f"lk_{s}", email=f"w8-lock-{s}@example.com", password_hash="x", role="customer"))
        await db.flush()
        db.add(Organization(id=f"lko_{s}", name="Lock", owner_id=f"lk_{s}", plan="trial", plan_id="plan_trial_default"))
        await db.commit()
    return f"lko_{s}"


async def _lock_while_archive_insert_is_open(org_id: str, s: str, key_share: bool) -> bool:
    """True when the workspace lock is granted while another transaction holds an FK insert."""
    async with engine.connect() as holder, engine.connect() as locker:
        await holder.begin()
        await holder.execute(text(
            "INSERT INTO ad_archive (id, org_id, archive_key, platform, media_status) "
            "VALUES (:i, :o, :k, 'meta', 'none')"
        ), {"i": f"lka_{s}_{key_share}", "o": org_id, "k": f"key_{s}_{key_share}"})
        await locker.begin()
        await locker.execute(text("SET LOCAL lock_timeout = '2s'"))
        try:
            await locker.execute(
                select(Organization.id).where(Organization.id == org_id).with_for_update(key_share=key_share)
            )
            granted = True
        except Exception as exc:  # lock_timeout
            assert "lock" in str(exc).lower()
            granted = False
        await locker.rollback()
        await holder.rollback()
    return granted


@pytest.mark.asyncio
async def test_no_key_update_lock_is_not_blocked_by_an_open_archive_insert():
    s = uuid.uuid4().hex[:8]
    org_id = await _workspace(s)
    assert await _lock_while_archive_insert_is_open(org_id, s, key_share=True) is True
    # The old plain FOR UPDATE is what waited (documented, so a regression is visible).
    assert await _lock_while_archive_insert_is_open(org_id, s, key_share=False) is False


def test_billing_locks_workspace_rows_with_no_key_update():
    import inspect

    from app.services import billing_service

    source = inspect.getsource(billing_service)
    assert "select(Organization).where(Organization.id == org_id).with_for_update()" not in source
    assert source.count("with_for_update(key_share=True)") >= 8
