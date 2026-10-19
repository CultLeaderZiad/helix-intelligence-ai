"""Canonical discovery cache regressions; local disposable PostgreSQL only."""
from __future__ import annotations

import asyncio
import datetime
import importlib.util
import uuid
from pathlib import Path
from types import SimpleNamespace
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import delete, event, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.session import worker_session_maker
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.schemas.discover import SearchParams
from app.services import discover_service


@pytest_asyncio.fixture
async def cache_db():
    url = make_url(settings.async_database_url)
    local = url.host in {"localhost", "127.0.0.1", "::1"} or url.query.get("host") == "/tmp/helix-w3"
    if not local or not ("w3" in (url.database or "") or url.database == "helix_test_db"):
        pytest.fail("Cache tests require a disposable local W3 database or CI helix_test_db")
    async with worker_session_maker() as db:
        suffix = uuid.uuid4().hex
        user = User(id=f"cache_u_{suffix}", email=f"{suffix}@example.test", password_hash="x", role="member")
        db.add(user)
        await db.flush()
        org = Organization(id=f"cache_o_{suffix}", owner_id=user.id, name="Cache test", plan="pro")
        db.add(org)
        await db.flush()
        try:
            yield db, user, org
        finally:
            await db.rollback()


def mocks(org):
    stack = ExitStack()
    stack.enter_context(patch.object(discover_service, "get_or_create_default_org", new=AsyncMock(return_value=org)))
    stack.enter_context(patch.object(discover_service, "assert_can_spend", new=AsyncMock(return_value=(org, None))))
    stack.enter_context(patch.object(discover_service, "translate_search_query", new=AsyncMock(side_effect=lambda query, lang: query)))
    stack.enter_context(patch.object(discover_service, "charge", new=AsyncMock()))
    stack.enter_context(patch("app.services.work_outbox.enqueue_work", new=AsyncMock()))
    stack.enter_context(patch("app.services.work_outbox.inline_execution_enabled", return_value=False))
    return stack


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["running", "succeeded"])
async def test_legacy_query_only_rows_fail_closed(cache_db, status):
    db, user, org = cache_db
    legacy = ScrapeJob(org_id=org.id, query="Nike", status=status, record_count=12)
    db.add(legacy)
    await db.flush()
    with mocks(org):
        response = await discover_service.trigger_search(db, SearchParams(query="Nike", filters={"country": "US"}), user.id)
    assert response.job_id != legacy.id


def test_canonical_identity_is_stable_complete_and_namespaced():
    from app.services.discovery_cache import discovery_cache_identity
    filters = {"country": "US", "nested": {"platform": ["meta", "google"], "active": True}, "limit": 15}
    reordered = {"limit": 15, "nested": {"active": True, "platform": ["meta", "google"]}, "country": "US"}
    def key(**kw):
        args = dict(query=" Nike  Shoes ", filters=filters, org_id="org-a", provider="metapi", version="1")
        args.update(kw)
        return discovery_cache_identity(**args)
    assert key() == key(query="nike shoes", filters=reordered)
    for change in [dict(filters={**filters, "country": "GB"}), dict(filters={**filters, "extra": False}),
                   dict(filters={**filters, "nested": {"platform": ["google", "meta"], "active": True}}),
                   dict(org_id="org-b"), dict(provider="adyntel"), dict(version="2"), dict(query="adidas")]:
        assert key() != key(**change)
    assert key(filters=None) == key(filters={})
    with pytest.raises(ValueError):
        key(filters={"invalid": float("nan")})


@pytest.mark.parametrize("name", ["platforms", "formats", "spend_bands"])
def test_multiselect_filter_order_is_not_semantic(name):
    from app.services.discovery_cache import discovery_cache_identity
    def key(values):
        return discovery_cache_identity(query="nike", filters={name: values},
                                        org_id="org-a", provider="meta")
    assert key(["a", "b"]) == key(["b", "a", "a"])
    assert key(["a", "b"]) != key(["a", "c"])


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["running", "succeeded"])
async def test_persisted_filter_identity_and_equivalence(cache_db, status):
    db, user, org = cache_db
    with mocks(org):
        first = await discover_service.trigger_search(db, SearchParams(query=" Nike  Shoes ", filters={"country": "US", "platforms": ["meta", "google"], "formats": ["image", "video"], "spend_bands": ["low", "high"]}), user.id)
        row = await db.get(ScrapeJob, first.job_id)
        row.status, row.record_count = status, 15
        await db.flush()
        assert row.cache_identity
        # Force a fresh ORM load: identity must live in SQL, not a process cache.
        db.expire(row)
        same = await discover_service.trigger_search(db, SearchParams(query="nike shoes", filters={"spend_bands": ["high", "low"], "formats": ["video", "image"], "platforms": ["google", "meta"], "country": "US"}), user.id)
        different = await discover_service.trigger_search(db, SearchParams(query="nike shoes", filters={"country": "GB", "platforms": ["meta", "google"], "formats": ["image", "video"], "spend_bands": ["low", "high"]}), user.id)
    assert same.job_id == first.job_id
    assert different.job_id != first.job_id


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["org", "provider", "version"])
async def test_persisted_namespace_separates_results(cache_db, change):
    from app.services import discovery_cache
    db, user, org = cache_db
    with mocks(org), patch.object(discover_service, "_discovery_cache_provider_identity", return_value="provider-a"):
        first = await discover_service.trigger_search(db, SearchParams(query="nike"), user.id)
        row = await db.get(ScrapeJob, first.job_id)
        row.status, row.record_count = "succeeded", 10
        await db.flush()
        with ExitStack() as stack:
            if change == "org":
                other = Organization(id=f"other_{uuid.uuid4().hex}", owner_id=user.id, name="Other", plan="pro")
                db.add(other)
                await db.flush()
                stack.enter_context(patch.object(discover_service, "assert_can_spend", new=AsyncMock(return_value=(other, None))))
            elif change == "provider":
                stack.enter_context(patch.object(discover_service, "_discovery_cache_provider_identity", return_value="provider-b"))
            else:
                stack.enter_context(patch.object(discovery_cache, "DISCOVERY_CACHE_VERSION", "next-version"))
            second = await discover_service.trigger_search(db, SearchParams(query="nike"), user.id)
    assert first.job_id != second.job_id


@pytest.mark.asyncio
async def test_authorization_and_entitlement_precede_every_cache_read(cache_db):
    db, user, org = cache_db
    statements = []
    connection = await db.connection()
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(connection.sync_connection, "before_cursor_execute", capture)
    try:
        with mocks(org), patch.object(discover_service, "assert_can_spend", new=AsyncMock(side_effect=HTTPException(403))):
            with pytest.raises(HTTPException) as denied:
                await discover_service.trigger_search(db, SearchParams(query="nike"), user.id)
            assert denied.value.status_code == 403
        assert not any("FROM scrape_jobs" in sql for sql in statements)
        statements.clear()
        with mocks(org):
            with pytest.raises(HTTPException) as denied:
                await discover_service.trigger_search(db, SearchParams(query="nike"), "missing-user")
            assert denied.value.status_code == 401
        assert not any("FROM scrape_jobs" in sql for sql in statements)
    finally:
        event.remove(connection.sync_connection, "before_cursor_execute", capture)


@pytest.mark.asyncio
async def test_postgres_active_unique_index_covers_canonical_identity(cache_db):
    from app.services.discovery_cache import discovery_cache_identity
    db, user, org = cache_db
    key = discovery_cache_identity(query="nike", filters={"country": "US"}, org_id=org.id, provider="meta")
    db.add(ScrapeJob(org_id=org.id, query="Nike", status="running", cache_identity=key))
    await db.flush()
    with pytest.raises(IntegrityError):
        async with db.begin_nested():
            db.add(ScrapeJob(org_id=org.id, query="NIKE", status="queued", cache_identity=key))
            await db.flush()
    # Different filters on the exact same query must no longer collide.
    other = discovery_cache_identity(query="nike", filters={"country": "GB"}, org_id=org.id, provider="meta")
    db.add(ScrapeJob(org_id=org.id, query="Nike", status="running", cache_identity=other))
    await db.flush()
    indexes = (await db.execute(text("SELECT indexname FROM pg_indexes WHERE tablename='scrape_jobs'"))).scalars().all()
    assert "uq_scrape_jobs_active_identity" in indexes
    assert "uq_scrape_jobs_active_query" not in indexes


@pytest.mark.asyncio
async def test_downgrade_with_distinct_active_filter_jobs_aborts_without_data_loss(cache_db):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from app.services.discovery_cache import discovery_cache_identity
    db, user, org = cache_db
    for country in ("US", "GB"):
        key = discovery_cache_identity(query="Nike", filters={"country": country}, org_id=org.id, provider="meta")
        db.add(ScrapeJob(org_id=org.id, query="Nike", status="running", cache_identity=key))
    await db.flush()
    path = Path(__file__).parents[1] / "alembic/versions/a9d4e6f8c2b0_w3_discovery_cache_identity.py"
    spec = importlib.util.spec_from_file_location("w3_cache_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    def downgrade(connection):
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
    with pytest.raises(IntegrityError):
        async with db.begin_nested():
            connection = await db.connection()
            await connection.run_sync(downgrade)
    rows = (await db.execute(select(ScrapeJob).where(ScrapeJob.org_id == org.id))).scalars().all()
    assert len(rows) == 2 and all(row.cache_identity for row in rows)
    indexes = (await db.execute(text("SELECT indexname FROM pg_indexes WHERE tablename='scrape_jobs'"))).scalars().all()
    assert "uq_scrape_jobs_active_identity" in indexes
    assert "uq_scrape_jobs_active_query" not in indexes


@pytest.mark.asyncio
@pytest.mark.parametrize("record_count,age_hours,status", [(0, 0, "succeeded"), (10, 13, "succeeded"), (10, 0, "failed")])
async def test_empty_expired_and_failed_results_are_not_reused(cache_db, record_count, age_hours, status):
    db, user, org = cache_db
    with mocks(org):
        first = await discover_service.trigger_search(db, SearchParams(query="nike"), user.id)
        row = await db.get(ScrapeJob, first.job_id)
        row.status, row.record_count = status, record_count
        row.created_at = discover_service._utcnow() - datetime.timedelta(hours=age_hours)
        await db.flush()
        second = await discover_service.trigger_search(db, SearchParams(query="nike"), user.id)
        assert second.job_id != first.job_id


def test_provider_configuration_identity_tracks_enabled_chain_not_credentials():
    provider = SimpleNamespace(
        metapi_provider=SimpleNamespace(metapi_api_key="synthetic-key-one"),
        adyntel_provider=SimpleNamespace(adyntel_api_key="", adyntel_email=""),
        meta_token="", apify_token="", meta_graph_version="v21.0",
    )
    with patch.object(discover_service, "AdLibraryProvider", return_value=provider), \
         patch("app.services.scraping.ad_library_provider._apify_allowed", return_value=True):
        first = discover_service._discovery_cache_provider_identity()
        assert first == "metapi;meta_graph=v21.0"
        provider.metapi_provider.metapi_api_key = "synthetic-key-two"
        assert discover_service._discovery_cache_provider_identity() == first
        provider.meta_token = "synthetic-token"
        assert discover_service._discovery_cache_provider_identity() != first
        provider.meta_token = ""
        provider.apify_token = "synthetic-token"
        assert discover_service._discovery_cache_provider_identity() != first
        with patch("app.services.scraping.ad_library_provider._apify_allowed", return_value=False):
            assert discover_service._discovery_cache_provider_identity() == first


@pytest.mark.asyncio
@pytest.mark.parametrize("different_filters", [False, True])
async def test_concurrent_requests_use_database_uniqueness(cache_db, different_filters):
    db, user, org = cache_db
    user_id, org_id = user.id, org.id
    await db.commit()  # The independent request sessions must see the fixture.
    barrier = asyncio.Barrier(2)

    async def request(country):
        async with worker_session_maker() as request_db:
            execute = request_db.execute
            async def synchronized_execute(statement, *args, **kwargs):
                result = await execute(statement, *args, **kwargs)
                # Both requests observe the completed-result miss before either
                # inserts. This exercises the unique-index recovery, not merely
                # a sequential read hitting an already committed active job.
                if "scrape_jobs.record_count >" in str(statement):
                    await barrier.wait()
                return result
            with patch.object(request_db, "execute", side_effect=synchronized_execute):
                result = await discover_service.trigger_search(request_db, SearchParams(query="Nike", filters={"country": country}), user_id)
                await request_db.commit()
                return result.job_id
    try:
        with mocks(org), patch.object(discover_service, "charge", new=AsyncMock()) as charge:
            ids = await asyncio.wait_for(asyncio.gather(request("US"), request("GB" if different_filters else "US")), timeout=15)
            assert len(set(ids)) == (2 if different_filters else 1)
            assert charge.await_count == (2 if different_filters else 1)
        count = await db.scalar(select(func.count()).select_from(ScrapeJob).where(ScrapeJob.org_id == org_id))
        assert count == (2 if different_filters else 1)
    finally:
        await db.rollback()
        await db.execute(delete(ScrapeJob).where(ScrapeJob.org_id == org_id))
        await db.execute(delete(Organization).where(Organization.id == org_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()
