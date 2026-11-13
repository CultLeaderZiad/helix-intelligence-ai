"""W9-1: archive search (Postgres FTS, simple + arabic) and the per-workspace
monthly Metapi record cap. No provider is called; DB tests use the test DB."""
from __future__ import annotations

import importlib.util
import pathlib
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.ad_archive import AdArchiveEntry
from app.models.organization import Organization
from app.models.user import User
from app.schemas.pricing import PlanLimits
from app.services import archive_service, provider_budget, text_search

MIGRATION = pathlib.Path(__file__).parents[1] / "alembic" / "versions" / "f2b4c6d8e0a1_w9_search_and_record_cap.py"


def _migration():
    spec = importlib.util.spec_from_file_location("w9_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_index_expressions_match_the_query_expressions():
    m = _migration()
    assert m.ARCHIVE_DOC == text_search.document_sql("ad_archive")
    assert m.CREATIVES_DOC == text_search.document_sql("creatives")
    assert m.down_revision == "e1a3c5e7f9b2"


def test_record_estimates_and_cap_defaults():
    assert provider_budget.search_record_estimate() == settings.METAPI_RESOLVE_COUNT + 15
    assert provider_budget.monitor_month_estimate("weekly") == 5 * provider_budget.search_record_estimate()
    assert provider_budget.monitor_month_estimate("daily") == 31 * provider_budget.search_record_estimate()
    assert settings.METAPI_WORKSPACE_MONTHLY_RECORD_CAP == 300
    assert provider_budget.workspace_record_cap({}) == 300
    assert provider_budget.workspace_record_cap({"records_per_month": 90}) == 90
    assert PlanLimits(records_per_month=500).records_per_month == 500
    with pytest.raises(ValueError):
        PlanLimits(records_per_month=-1)


def test_query_cleaning_bounds_user_input():
    assert text_search.clean_query("  a   b ") == "a b"
    assert len(text_search.clean_query("x" * 500)) == text_search.MAX_QUERY_LENGTH


async def _workspace(db, suffix, **org):
    user = User(id=f"u_{suffix}", email=f"w9-{suffix}@example.com", password_hash="x", role="member")
    db.add(user)
    await db.flush()
    o = Organization(id=f"o_{suffix}", name="W9", owner_id=user.id, plan="pro", **org)
    db.add(o)
    await db.flush()
    return user, o


@pytest.mark.asyncio
async def test_archive_search_matches_english_and_arabic_and_stays_in_the_workspace():
    suffix = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        user, org = await _workspace(db, suffix)
        for key, brand, headline, body in (
            ("a", "Gymshark", "Summer running shorts", "Lightweight shorts for runners"),
            ("b", "متجر الورد", "عروض العيد", "خصومات على الهدايا والورود"),
            ("c", "Acme", "Kitchen knives", "Sharp steel"),
        ):
            db.add(AdArchiveEntry(org_id=org.id, archive_key=f"meta:{suffix}{key}", platform="meta",
                                  brand_name=brand, headline=headline, body=body))
        stranger, other = await _workspace(db, suffix + "x")
        db.add(AdArchiveEntry(org_id=other.id, archive_key=f"meta:{suffix}z", platform="meta",
                              brand_name="Gymshark", headline="shorts", body="other workspace"))
        await db.commit()

        en = await archive_service.search(db, user, "running shorts", scope="archive")
        assert en["records_used"] == 0
        assert [i["brand_name"] for i in en["archive"]["items"]] == ["Gymshark"]
        ar = await archive_service.search(db, user, "خصومات", scope="archive")
        assert [i["brand_name"] for i in ar["archive"]["items"]] == ["متجر الورد"]
        # Arabic stemming: the word without its article still matches.
        assert (await archive_service.search(db, user, "هدايا", scope="archive"))["archive"]["total"] == 1
        assert (await archive_service.search(db, user, "nothing-like-this", scope="archive"))["archive"]["total"] == 0
        # Websearch syntax never raises on odd input.
        await archive_service.search(db, user, "\"unclosed -('&|", scope="archive")
        assert (await archive_service.search(db, stranger, "running shorts", scope="archive"))["archive"]["total"] == 0
        with pytest.raises(HTTPException) as empty:
            await archive_service.search(db, user, "   ")
        assert empty.value.status_code == 422


@pytest.mark.asyncio
@pytest.mark.real_provider_budget
async def test_workspace_record_cap_refuses_and_rolls_back_both_counters(monkeypatch):
    monkeypatch.setattr(settings, "METAPI_WORKSPACE_MONTHLY_RECORD_CAP", 36)
    suffix = uuid.uuid4().hex[:8]
    provider = f"test-{suffix}"
    async with async_session_maker() as db:
        _user, org = await _workspace(db, suffix)
        await db.commit()
    assert await provider_budget.reserve_provider_records(provider, 30, 10_000, org_id=org.id) is True
    assert await provider_budget.reserve_provider_records(provider, 15, 10_000, org_id=org.id) is False
    async with async_session_maker() as db:
        usage = await provider_budget.workspace_record_usage(db, org.id)
        global_used = (await db.execute(text(
            "SELECT records FROM provider_record_budget WHERE provider = :p "
            "AND period_start = date_trunc('month', now() AT TIME ZONE 'utc')::date"
        ), {"p": provider})).scalar_one()
        assert global_used == 30  # the refused reservation did not count globally either
        assert usage["used"] == 30 and usage["cap"] == 36 and usage["remaining"] == 6
        assert usage["warning"] is True and usage["reached"] is False and usage["percent"] == 83
        with pytest.raises(HTTPException) as refused:
            await provider_budget.assert_record_room(db, org.id, provider_budget.search_record_estimate())
        assert refused.value.status_code == 429
        assert refused.value.detail["code"] == "workspace_record_cap_reached"
        await provider_budget.assert_record_room(db, org.id, 6)


@pytest.mark.asyncio
async def test_w9_tables_keep_row_level_security_and_their_tenant_policies():
    """W9-1 only adds a column and indexes; RLS must stay on for every table it reads or writes."""
    async with async_session_maker() as db:
        rows = (await db.execute(text(
            "SELECT c.relname, c.relrowsecurity, "
            "(SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = c.relname) "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relname = ANY(:t)"
        ), {"t": ["ad_archive", "creatives", "saved_creatives", "workspace_daily_usage", "scrape_jobs"]})).all()
    found = {name: (enabled, policies) for name, enabled, policies in rows}
    assert set(found) == {"ad_archive", "creatives", "saved_creatives", "workspace_daily_usage", "scrape_jobs"}
    for name, (enabled, policies) in found.items():
        assert enabled is True, f"RLS is off on {name}"
        assert policies >= 1, f"{name} has no RLS policy"
