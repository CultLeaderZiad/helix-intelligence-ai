"""W9-2: tags and notes on saved ads, and one-click "Monitor this brand".

Nothing here calls a provider. DB tests use the repo's test database
(DATABASE_URL in CI), never backend/.env.local.
"""
from __future__ import annotations

import importlib.util
import pathlib
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text

from app.db.session import async_session_maker
from app.models.creative import Creative
from app.models.monitor import Monitor
from app.models.organization import Organization
from app.models.saved_ad_annotation import SavedAdNote, SavedAdTag
from app.models.saved_creative import SavedCreative
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.services import annotation_service, billing_service, creative_service, monitor_service, provider_budget
from app.services.creative_service import provenance_fields

MIGRATION = pathlib.Path(__file__).parents[1] / "alembic" / "versions" / "a4c6e8f0b2d5_w9_saved_ad_tags_notes.py"


def test_migration_follows_w9_1_and_covers_both_tables():
    spec = importlib.util.spec_from_file_location("w9_2_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == "f2b4c6d8e0a1"
    assert module.TABLES == ("saved_ad_tags", "saved_ad_notes")


def test_tag_and_note_cleaning():
    assert annotation_service.clean_tags(["  UGC  Hook ", "ugc hook", "عرض", ""]) == ["ugc hook", "عرض"]
    assert len(annotation_service.clean_tag("x" * 100)) == annotation_service.MAX_TAG_LENGTH
    with pytest.raises(HTTPException) as many:
        annotation_service.clean_tags([f"t{i}" for i in range(annotation_service.MAX_TAGS_PER_AD + 1)])
    assert many.value.detail["code"] == "too_many_tags"
    with pytest.raises(HTTPException):
        annotation_service.clean_note("   ")
    with pytest.raises(HTTPException):
        annotation_service.clean_note("x" * (annotation_service.MAX_NOTE_LENGTH + 1))


def test_brand_monitor_target_prefers_the_page_id():
    assert monitor_service.brand_monitor_target("123456789", "Gymshark") == {
        "query": "123456789", "name": "Gymshark", "watch": "page_id",
    }
    link = "https://www.facebook.com/ads/library/?view_all_page_id=987654321"
    assert monitor_service.brand_monitor_target(link, None)["query"] == "987654321"
    # Not a page id: fall back to the brand name.
    assert monitor_service.brand_monitor_target("abc", "  Acme  Co ") == {
        "query": "Acme Co", "name": "Acme Co", "watch": "brand_name",
    }
    with pytest.raises(HTTPException) as missing:
        monitor_service.brand_monitor_target(None, "  ")
    assert missing.value.status_code == 422


def test_page_id_is_exposed_only_when_it_is_digits():
    class C:
        provenance_json = {"raw": {"page_id": "123456"}}

    class Bad:
        provenance_json = {"raw": {"page_id": "12; drop"}}

    assert provenance_fields(C)["page_id"] == "123456"
    assert provenance_fields(Bad)["page_id"] is None


@pytest.fixture
def _swipe_files_on(monkeypatch):
    async def _allow(db, user, feature_name=None, required_credits=0.0, **_kw):
        return await billing_service.get_or_create_default_org(db, user), None

    monkeypatch.setattr(billing_service, "check_quota_and_feature", _allow)


async def _saved_ad(db, suffix, headline="Summer shorts"):
    user = User(id=f"u_{suffix}", email=f"w92-{suffix}@example.com", password_hash="x", role="member")
    db.add(user)
    await db.flush()
    org = Organization(id=f"o_{suffix}", name="W9-2", owner_id=user.id, plan="pro")
    db.add(org)
    await db.flush()
    job = ScrapeJob(id=f"j_{suffix}", org_id=org.id, query="shorts", status="succeeded")
    db.add(job)
    await db.flush()
    creative = Creative(id=f"c_{suffix}", job_id=job.id, brand_id=f"b_{suffix}", brand_name="Gymshark",
                        platform="meta", format="image", headline=headline, body="Lightweight", variant_count=1)
    db.add(creative)
    await db.flush()
    db.add(SavedCreative(user_id=user.id, org_id=org.id, creative_id=creative.id, collection_name="Default"))
    await db.commit()
    return user, org, creative


@pytest.mark.asyncio
async def test_tags_and_notes_crud_filter_search_and_cascade(_swipe_files_on):
    suffix = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        user, org, creative = await _saved_ad(db, suffix)
        stranger, _o, _c = await _saved_ad(db, suffix + "x", headline="Kitchen knives")

        out = await annotation_service.set_tags(db, user, creative.id, ["UGC hook", "Eid", "ugc hook"])
        assert out["tags"] == ["eid", "ugc hook"]
        out = await annotation_service.set_tags(db, user, creative.id, ["eid", "competitor"])
        assert out["tags"] == ["competitor", "eid"]
        assert {t["tag"] for t in await annotation_service.list_tags(db, user)} == {"competitor", "eid"}
        assert await annotation_service.list_tags(db, stranger) == []

        note = await annotation_service.add_note(db, user, creative.id, "Strong hook, copy the opening")
        edited = await annotation_service.update_note(db, user, creative.id, note["id"], "خطاف قوي في البداية")
        assert edited["body"] == "خطاف قوي في البداية" and edited["updated_at"]

        # Someone else cannot tag, note or edit an ad they did not save.
        with pytest.raises(HTTPException) as nope:
            await annotation_service.set_tags(db, stranger, creative.id, ["x"])
        assert nope.value.status_code == 404
        with pytest.raises(HTTPException):
            await annotation_service.update_note(db, stranger, creative.id, note["id"], "x")

        tagged = await creative_service.list_saved_creatives(db, user, tag="EID")
        assert [i.id for i in tagged.items] == [creative.id]
        assert tagged.items[0].tags == ["competitor", "eid"]
        assert tagged.items[0].notes[0].body == "خطاف قوي في البداية"
        assert (await creative_service.list_saved_creatives(db, user, tag="missing")).total == 0
        # Archive/board search matches tags and note text, not only ad copy.
        assert (await creative_service.list_saved_creatives(db, user, q="competitor")).total == 1
        assert (await creative_service.list_saved_creatives(db, user, q="خطاف")).total == 1
        assert (await creative_service.list_saved_creatives(db, stranger, q="competitor")).total == 0

        rows = (await db.execute(select(SavedAdTag.org_id).where(SavedAdTag.created_by == user.id))).scalars().all()
        assert rows and set(rows) == {org.id}

        await annotation_service.delete_note(db, user, creative.id, note["id"])
        await annotation_service.add_note(db, user, creative.id, "kept until unsave")
        await creative_service.unsave_creative(db, user, creative.id)
        left_tags = (await db.execute(select(SavedAdTag).where(SavedAdTag.created_by == user.id))).all()
        left_notes = (await db.execute(select(SavedAdNote).where(SavedAdNote.author_id == user.id))).all()
        assert left_tags == [] and left_notes == []


@pytest.mark.asyncio
async def test_brand_monitor_preview_costs_records_and_respects_the_cap(monkeypatch):
    suffix = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        user = User(id=f"u_{suffix}", email=f"w92m-{suffix}@example.com", password_hash="x", role="member")
        db.add(user)
        await db.flush()
        org = Organization(id=f"o_{suffix}", name="W9-2", owner_id=user.id, plan="pro")
        db.add(org)
        await db.commit()

        preview = await monitor_service.brand_monitor_preview(
            db, org_id=org.id, page_id="123456789", brand_name="Gymshark", cadence="weekly"
        )
        assert preview["query"] == "123456789" and preview["watch"] == "page_id"
        assert preview["records_per_run"] == provider_budget.search_record_estimate()
        assert preview["records_per_month"] == provider_budget.monitor_month_estimate("weekly")
        assert preview["existing_monitor_id"] is None

        db.add(Monitor(org_id=org.id, user_id=user.id, name="Gymshark", query="123456789", filters={},
                       cadence="weekly", status="active"))
        await db.commit()
        again = await monitor_service.brand_monitor_preview(db, org_id=org.id, page_id="123456789", brand_name=None)
        assert again["existing_monitor_id"]

        async def _full(_db, _org_id, needed):
            raise HTTPException(status_code=429, detail={"code": "workspace_record_cap_reached"})

        monkeypatch.setattr(provider_budget, "assert_record_room", _full)
        with pytest.raises(HTTPException) as capped:
            await monitor_service._enforce_plan_monitor_limits(db, org.id, "weekly", activating=True)
        assert capped.value.status_code == 429


@pytest.mark.asyncio
async def test_w9_2_tables_have_row_level_security_and_a_tenant_policy():
    async with async_session_maker() as db:
        rows = (await db.execute(text(
            "SELECT c.relname, c.relrowsecurity, "
            "(SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = c.relname "
            " AND p.policyname = c.relname || '_tenant_isolation') "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relname = ANY(:t)"
        ), {"t": ["saved_ad_tags", "saved_ad_notes"]})).all()
    assert {r[0]: (r[1], r[2]) for r in rows} == {"saved_ad_tags": (True, 1), "saved_ad_notes": (True, 1)}
