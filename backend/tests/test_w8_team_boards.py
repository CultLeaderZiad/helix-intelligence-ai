"""W8: team boards are readable by current members only, and only behind `team_accounts`."""
from __future__ import annotations

import inspect
import uuid

import pytest
from fastapi import HTTPException

from app.api.routers import boards
from app.db.session import async_session_maker
from app.models.creative import Creative
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.saved_creative import SavedCreative
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.services import team_board_service as svc


def test_team_routes_require_the_team_accounts_flag():
    source = inspect.getsource(boards)
    assert '_team = [Depends(require_feature("team_accounts"))]' in source
    for path in ("/team", "/team/items"):
        route = next(r for r in boards.router.routes if r.path == path)
        assert route.dependencies, path


@pytest.mark.asyncio
async def test_members_read_each_others_boards_but_former_members_and_strangers_do_not_appear():
    s = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        owner = User(id=f"a_{s}", email=f"w8-team-a-{s}@example.com", password_hash="x", role="member", full_name="Ana")
        member = User(id=f"m_{s}", email=f"w8-team-m-{s}@example.com", password_hash="x", role="member")
        former = User(id=f"f_{s}", email=f"w8-team-f-{s}@example.com", password_hash="x", role="member")
        stranger = User(id=f"x_{s}", email=f"w8-team-x-{s}@example.com", password_hash="x", role="member")
        db.add_all([owner, member, former, stranger])
        await db.flush()
        org = Organization(id=f"o_{s}", name="Team", owner_id=owner.id, plan="pro")
        other = Organization(id=f"p_{s}", name="Other", owner_id=stranger.id, plan="pro")
        db.add_all([org, other])
        await db.flush()
        db.add(OrganizationMember(org_id=org.id, user_id=member.id, role="member"))
        member.signup_metadata = {"active_org_id": org.id}
        job = ScrapeJob(id=f"j_{s}", org_id=org.id, query="team", status="succeeded")
        db.add(job)
        await db.flush()
        for key, who, board in (("1", owner, "Hooks"), ("2", owner, "Hooks"), ("3", member, "Mine"), ("4", former, "Old")):
            cid = f"c_{s}_{key}"
            db.add(Creative(id=cid, job_id=job.id, brand_id="b", brand_name="Brand", platform="meta",
                            format="image", headline=f"h{key}", days_active=None))
            await db.flush()
            db.add(SavedCreative(user_id=who.id, org_id=org.id, creative_id=cid, collection_name=board))
        await db.commit()

        listed = await svc.list_team_boards(db, member)
        assert {(b["owner_id"], b["name"], b["count"]) for b in listed} == {(owner.id, "Hooks", 2), (member.id, "Mine", 1)}
        assert next(b for b in listed if b["owner_id"] == owner.id)["owner_name"] == "Ana"

        board = await svc.get_team_board(db, member, owner.id, "Hooks")
        assert board["read_only"] is True and len(board["items"]) == 2
        assert all(item["days_active"] is None for item in board["items"])

        with pytest.raises(HTTPException) as gone:
            await svc.get_team_board(db, member, former.id, "Old")
        assert gone.value.status_code == 404

        assert await svc.list_team_boards(db, stranger) == []
        with pytest.raises(HTTPException) as outside:
            await svc.get_team_board(db, stranger, owner.id, "Hooks")
        assert outside.value.status_code == 404


def test_team_list_owner_row_does_not_read_a_missing_organization_column():
    """GET /account/team returned 500 (AttributeError) when the workspace owner
    was not in organization_members: it read Organization.created_at, which
    does not exist. The owner row now uses the owner's account date."""
    from app.services import team_service

    assert not hasattr(Organization, "created_at")
    source = inspect.getsource(team_service.list_team)
    assert "org.created_at" not in source
    assert 'getattr(owner_user, "created_at", None)' in source
