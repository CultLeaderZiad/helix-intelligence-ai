"""Ask Helix saved conversations: private per user, bounded memory, archive instead of delete, RLS."""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.api.routers import agent
from app.db.session import async_session_maker, engine
from app.models.organization import Organization
from app.models.user import User
from app.services import agent_conversation_service as svc


def test_title_comes_from_the_first_question_and_is_bounded():
    assert svc.title_from("  what   do my   monitors say  ") == "what do my monitors say"
    long = svc.title_from("x" * 200)
    assert len(long) == 61 and long.endswith("…")
    assert svc.title_from("   ") == "New chat"


def test_memory_is_bounded():
    assert svc.MEMORY_TURNS <= 6 and svc.MEMORY_CHARS <= 500 and svc.MAX_ACTIVE == 50


def test_routes_exist_and_ask_accepts_a_conversation_id():
    paths = {(r.path, tuple(sorted(r.methods))) for r in agent.router.routes}
    assert ("/conversations", ("GET",)) in paths
    assert ("/conversations/{conversation_id}", ("GET",)) in paths
    assert ("/conversations/{conversation_id}", ("PATCH",)) in paths
    assert ("/conversations/{conversation_id}", ("DELETE",)) in paths
    assert "conversation_id" in agent.AskBody.model_fields
    assert agent.router.dependencies, "agent router must keep require_feature('discover')"


async def _two_users(s: str):
    async with async_session_maker() as db:
        a = User(id=f"cva_{s}", email=f"cv-a-{s}@example.com", password_hash="x", role="customer")
        b = User(id=f"cvb_{s}", email=f"cv-b-{s}@example.com", password_hash="x", role="customer")
        db.add_all([a, b])
        await db.flush()
        org = Organization(id=f"cvo_{s}", name="Org", owner_id=a.id, plan="trial")
        db.add(org)
        await db.commit()
    return a, b, org.id


ANSWER = {"answer": "Here you go", "citations": [], "proposals": [], "model": "m", "label": "AI"}


@pytest.mark.asyncio
async def test_a_turn_is_saved_and_only_its_owner_can_read_or_continue_it():
    a, b, org = await _two_users(uuid.uuid4().hex[:8])
    async with async_session_maker() as db:
        cid = await svc.record_turn(db, a, org, None, "What is new?", ANSWER)
        await svc.record_turn(db, a, org, cid, "And last week?", ANSWER)
        opened = await svc.get_conversation(db, a, org, cid)
        assert [m["role"] for m in opened["messages"]] == ["user", "assistant", "user", "assistant"]
        assert opened["title"] == "What is new?"
        memory = await svc.history_for_model(db, a, org, cid)
        assert [m["role"] for m in memory] == ["user", "assistant", "user", "assistant"]
        for other in (svc.get_conversation, svc.history_for_model):
            with pytest.raises(HTTPException) as exc:
                await other(db, b, org, cid)
            assert exc.value.status_code == 404
        with pytest.raises(HTTPException):
            await svc.record_turn(db, b, org, cid, "hijack", ANSWER)


@pytest.mark.asyncio
async def test_past_the_cap_the_oldest_unpinned_is_archived_not_deleted():
    a, _b, org = await _two_users(uuid.uuid4().hex[:8])
    async with async_session_maker() as db:
        first = await svc.record_turn(db, a, org, None, "first", ANSWER)
        await svc.update_conversation(db, a, org, first, pinned=True)
        ids = [await svc.record_turn(db, a, org, None, f"q{i}", ANSWER) for i in range(svc.MAX_ACTIVE)]
        active = {c["id"] for c in await svc.list_conversations(db, a, org)}
        archived = {c["id"] for c in await svc.list_conversations(db, a, org, archived=True)}
        assert first in active, "pinned stays"
        assert ids[0] in archived and ids[-1] in active
        assert len(active) <= svc.MAX_ACTIVE
        assert (await svc.get_conversation(db, a, org, ids[0]))["messages"], "archived is still readable"


@pytest.mark.asyncio
async def test_delete_removes_its_messages():
    a, _b, org = await _two_users(uuid.uuid4().hex[:8])
    async with async_session_maker() as db:
        cid = await svc.record_turn(db, a, org, None, "bye", ANSWER)
        await svc.delete_conversation(db, a, org, cid)
        left = (await db.execute(text("SELECT count(*) FROM agent_messages WHERE conversation_id = :c"), {"c": cid})).scalar()
        assert left == 0


@pytest.mark.asyncio
async def test_rls_isolates_users_inside_one_workspace_and_across_workspaces():
    """Run as the restricted helix_app role, the way the API connects in production."""
    s = uuid.uuid4().hex[:8]
    a, b, org = await _two_users(s)
    async with async_session_maker() as db:
        cid = await svc.record_turn(db, a, org, None, "private", ANSWER)

    async def visible(user_id: str, org_ids: str, admin: str = "0"):
        async with engine.connect() as conn:
            async with conn.begin():
                await conn.execute(text("SET LOCAL ROLE helix_app"))
                await conn.execute(text(
                    "SELECT set_config('helix.user_id', :u, true), set_config('helix.org_ids', :o, true), "
                    "set_config('helix.platform_admin', :a, true), set_config('helix.enforce', '1', true)"
                ), {"u": user_id, "o": org_ids, "a": admin})
                convs = (await conn.execute(text("SELECT id FROM agent_conversations WHERE id = :c"), {"c": cid})).scalars().all()
                msgs = (await conn.execute(text("SELECT id FROM agent_messages WHERE conversation_id = :c"), {"c": cid})).scalars().all()
                await conn.execute(text("RESET ROLE"))
        return len(convs), len(msgs)

    assert await visible(a.id, org) == (1, 2)
    assert await visible(b.id, org) == (0, 0), "another user in the same workspace sees nothing"
    assert await visible(a.id, "someone-else") == (0, 0), "the same user outside the workspace sees nothing"
    assert await visible("", "") == (0, 0)
    assert await visible("", "", admin="1") == (1, 2)
