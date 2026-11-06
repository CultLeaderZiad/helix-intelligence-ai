"""W8: saved Discover search drafts live on the server, per user per workspace."""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.api.routers import discover
from app.db.session import async_session_maker
from app.models.organization import Organization
from app.models.user import User
from app.schemas.discover import Job
from app.services import search_draft_service as svc


def test_draft_routes_sit_behind_the_discover_feature():
    paths = {(route.path, tuple(sorted(route.methods))) for route in discover.router.routes}
    assert ("/drafts", ("GET",)) in paths
    assert ("/drafts", ("POST",)) in paths
    assert ("/drafts/{draft_id}", ("DELETE",)) in paths
    assert discover.router.dependencies, "discover router must keep require_feature('discover')"


def test_filters_keep_only_what_the_results_view_understands():
    assert svc._clean_filters({"country": "US", "min_days_active": 90, "min_score": 7, "spend": "x", "evil": 1}) == {
        "country": "US", "min_days_active": 90, "min_score": 7,
    }
    assert svc._clean_filters({"min_days_active": -1, "country": "x" * 40}) == {}
    assert svc._clean_filters(None) == {}


def test_job_rows_carry_the_query_for_server_side_history():
    assert "query" in Job.model_fields


@pytest.mark.asyncio
async def test_drafts_are_private_to_their_owner_and_deletable_only_by_them():
    s = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        owner = User(id=f"d_{s}", email=f"w8-draft-{s}@example.com", password_hash="x", role="member")
        other = User(id=f"e_{s}", email=f"w8-draft-o-{s}@example.com", password_hash="x", role="member")
        db.add_all([owner, other])
        await db.flush()
        db.add_all([
            Organization(id=f"o_{s}", name="Drafts", owner_id=owner.id, plan="pro"),
            Organization(id=f"p_{s}", name="Other", owner_id=other.id, plan="pro"),
        ])
        await db.commit()

        saved = await svc.save_draft(db, owner, title="", query="  nike running ", notes="n", filters={"country": "US", "x": 1})
        assert saved["title"] == "nike running" and saved["query"] == "nike running"
        assert saved["filters"] == {"country": "US"}

        assert [d["id"] for d in await svc.list_drafts(db, owner)] == [saved["id"]]
        assert await svc.list_drafts(db, other) == []

        with pytest.raises(HTTPException) as denied:
            await svc.delete_draft(db, other, saved["id"])
        assert denied.value.status_code == 404

        with pytest.raises(HTTPException) as empty:
            await svc.save_draft(db, owner, title="t", query="   ")
        assert empty.value.status_code == 422

        assert (await svc.delete_draft(db, owner, saved["id"]))["deleted"] == saved["id"]
        assert await svc.list_drafts(db, owner) == []
