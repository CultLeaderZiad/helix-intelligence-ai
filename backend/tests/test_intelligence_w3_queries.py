"""W3 SQL bounds on a disposable, migrated PostgreSQL database only.

No provider requests or production data; every seeded row is rolled back.
"""
from __future__ import annotations

import json
import re
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import event

from app.core.config import settings
from app.db.session import worker_session_maker
from app.models.ai_insight import AIInsight
from app.models.creative import Creative
from app.models.organization import Organization
from app.models.pattern import Pattern
from app.models.playbook import Playbook
from app.models.scrape_job import ScrapeJob
from app.models.saved_creative import SavedCreative
from app.models.user import User
from app.schemas.discover import SearchParams
from app.services import analysis_service, creative_service, discover_service, playbook_service


@pytest_asyncio.fixture
async def corpus():
    # Explicit opt-in prevents accidental execution against a configured remote DB.
    from sqlalchemy.engine import make_url
    url = make_url(settings.async_database_url)
    local = url.host in {"localhost", "127.0.0.1", "::1"} or url.query.get("host") == "/tmp/helix-w3"
    # The repository CI creates helix_test_db in a fresh PostgreSQL service.
    # Accept that known disposable name as well as local W3 databases, never
    # a remote/configured production database or an arbitrary local database.
    disposable = "w3" in (url.database or "") or url.database == "helix_test_db"
    if not local or not disposable:
        pytest.fail("W3 query tests require a disposable local W3 database or CI helix_test_db")
    suffix = uuid.uuid4().hex
    async with worker_session_maker() as db:
        db.add_all([
            User(id=f"u_{suffix}_{i}", email=f"{suffix}_{i}@example.test", password_hash="x", role="member")
            for i in range(2)
        ])
        await db.flush()
        users = [f"u_{suffix}_{i}" for i in range(2)]
        orgs = [f"o_{suffix}_{i}" for i in range(2)]
        jobs = [f"j_{suffix}_{i}" for i in range(2)]
        db.add_all([Organization(id=orgs[i], name="W3 test", owner_id=users[i], plan="pro") for i in range(2)])
        await db.flush()
        db.add_all([ScrapeJob(id=jobs[i], org_id=orgs[i], query="test", status="succeeded", record_count=140) for i in range(2)])
        await db.flush()
        # Enough brands and records to exceed both default and maximum pages.
        db.add_all([
            Creative(id=f"c_{suffix}_{i}_{j:03}", job_id=jobs[i], brand_id=f"brand_{j // 2:03}",
                     brand_name=f"Brand {j // 2}", platform="meta", format="image")
            for i in range(2) for j in range(140)
        ])
        await db.flush()
        db.add_all([
            AIInsight(id=f"i_{suffix}_{i}_{j:03}", creative_id=f"c_{suffix}_{i}_{j:03}",
                      title="Insight", summary="Summary", confidence=0.5)
            for i in range(2) for j in range(140)
        ])
        db.add_all([
            Pattern(id=f"p_{suffix}_{i}_{j:03}", job_id=jobs[i], org_id=orgs[i], label="Pattern", family="hook", prevalence=0.5)
            for i in range(2) for j in range(25)
        ])
        db.add_all([
            Playbook(id=f"b_{suffix}_{i}_{j:03}", public_id=f"pb_{suffix}_{i}_{j}", user_id=users[i], org_id=orgs[i],
                     brand_name="Brand", query="test", title="Playbook")
            for i in range(2) for j in range(25)
        ])
        await db.flush()
        statements = []
        connection = await db.connection()

        def capture(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(connection.sync_connection, "before_cursor_execute", capture)
        try:
            yield db, users, orgs, jobs, suffix, statements
        finally:
            event.remove(connection.sync_connection, "before_cursor_execute", capture)
            await db.rollback()


@pytest.mark.asyncio
async def test_brand_count_and_page_stay_in_sql(corpus):
    db, users, orgs, jobs, suffix, statements = corpus
    result = await creative_service.list_brands(db, page=2, page_size=7, user_org_ids=[orgs[0]])
    assert result.total == 70
    assert result.page == 2 and result.page_size == 7 and result.has_more
    assert [brand.id for brand in result.items] == [f"brand_{j:03}" for j in range(7, 14)]
    assert all(brand.ad_count == 2 for brand in result.items)
    assert len(statements) == 2
    assert "count(" in statements[0].lower() and "GROUP BY" in statements[0]
    assert "LIMIT" in statements[1] and "OFFSET" in statements[1] and "ORDER BY" in statements[1]


@pytest.mark.asyncio
async def test_insights_scope_is_a_database_subquery_not_materialized_ids(corpus):
    db, users, orgs, jobs, suffix, statements = corpus
    result = await analysis_service.list_insights(db, page=2, page_size=9, user_org_ids=[orgs[0]])
    assert result.total == 140 and len(result.items) == 9 and result.has_more
    assert [item.id for item in result.items] == [f"i_{suffix}_0_{j:03}" for j in range(9, 18)]
    assert len(statements) == 2  # count + bounded page, never an org-wide ID fetch
    assert all("JOIN scrape_jobs" in statement and "IN (SELECT creatives.id" in statement for statement in statements)
    assert "LIMIT" in statements[1] and "ORDER BY" in statements[1]
    empty = await analysis_service.list_insights(db, user_org_ids=[])
    assert empty.total == 0 and empty.items == []


@pytest.mark.asyncio
async def test_creatives_and_patterns_keep_scope_and_stable_pages(corpus):
    db, users, orgs, jobs, suffix, statements = corpus
    first = await creative_service.list_creatives(db, job_id=jobs[0], brand_id="brand_004", page_size=1, user_org_ids=[orgs[0]])
    second = await creative_service.list_creatives(db, job_id=jobs[0], brand_id="brand_004", page=2, page_size=1, user_org_ids=[orgs[0]])
    assert first.total == second.total == 2
    assert [first.items[0].id, second.items[0].id] == [f"c_{suffix}_0_008", f"c_{suffix}_0_009"]
    denied = await creative_service.list_creatives(db, job_id=jobs[1], user_org_ids=[orgs[0]])
    assert denied.items == [] and denied.total == 0
    patterns = await creative_service.list_patterns(db, page=2, page_size=10, user_org_ids=[orgs[0]])
    assert patterns.total == 25 and len(patterns.items) == 10
    assert all(item.id.startswith(f"p_{suffix}_0_") for item in patterns.items)
    assert all("LIMIT" in statement and "ORDER BY" in statement for statement in statements if "count(" not in statement.lower())


@pytest.mark.asyncio
async def test_recent_jobs_sql_scope_order_and_bounds(corpus):
    db, users, orgs, jobs, suffix, statements = corpus
    with patch.object(settings, "USE_MOCKS", False):
        result = await discover_service.list_recent_jobs(db, users[0], page_size=1)
    assert result.total == 1 and [item.job_id for item in result.items] == [jobs[0]]
    assert len(statements) == 2 and "ORDER BY" in statements[1] and "LIMIT" in statements[1]


@pytest.mark.asyncio
async def test_max_page_size_empty_last_page_and_empty_scope(corpus):
    db, users, orgs, jobs, suffix, statements = corpus
    page = await creative_service.list_creatives(db, page_size=100, user_org_ids=[orgs[0]])
    assert len(page.items) == 100 and page.total == 140 and page.has_more
    last = await creative_service.list_creatives(db, page=3, page_size=100, user_org_ids=[orgs[0]])
    assert last.items == [] and last.total == 140 and not last.has_more
    empty = await creative_service.list_brands(db, user_org_ids=[])
    assert empty.items == [] and empty.total == 0
    empty_patterns = await creative_service.list_patterns(db, user_org_ids=[])
    assert empty_patterns.items == [] and empty_patterns.total == 0
    boundary = await analysis_service.list_insights(db, page=1000001, page_size=1, user_org_ids=[orgs[0]])
    assert boundary.items == [] and boundary.total == 140 and not boundary.has_more


@pytest.mark.asyncio
async def test_saved_creatives_filter_count_and_page_in_sql(corpus):
    db, users, orgs, jobs, suffix, statements = corpus
    db.add_all([
        SavedCreative(id=f"s_{suffix}_{i}_{j:03}", user_id=users[i], org_id=orgs[i],
                      creative_id=f"c_{suffix}_{i}_{j:03}", collection_name="Pick" if j < 12 else "Other")
        for i in range(2) for j in range(25)
    ])
    await db.flush()
    statements.clear()
    with patch("app.services.billing_service.check_quota_and_feature", new=AsyncMock()):
        result = await creative_service.list_saved_creatives(db, User(id=users[0]), collection_name="Pick", page=2, page_size=5)
    assert result.total == 12 and len(result.items) == 5 and result.has_more
    assert all(item.id.startswith(f"c_{suffix}_0_") for item in result.items)
    assert len(statements) == 2
    assert "saved_creatives.collection_name" in statements[0]
    assert "LIMIT" in statements[1] and "ORDER BY" in statements[1]


@pytest.mark.asyncio
async def test_per_creative_insights_are_bounded_and_counted(corpus):
    db, users, orgs, jobs, suffix, statements = corpus
    creative_id = f"c_{suffix}_0_000"
    db.add_all([
        AIInsight(id=f"extra_{suffix}_{j:03}", creative_id=creative_id, title="Extra", summary="Summary", confidence=0.5)
        for j in range(29)
    ])
    await db.flush()
    statements.clear()
    result = await analysis_service.get_creative_insight(db, creative_id, user_org_ids=[orgs[0]])
    assert result.total == 30 and len(result.items) == 20 and result.has_more
    second = await analysis_service.get_creative_insight(db, creative_id, user_org_ids=[orgs[0]], page=2)
    assert second.total == 30 and len(second.items) == 10 and not second.has_more
    assert set(item.id for item in result.items).isdisjoint(item.id for item in second.items)
    denied = await analysis_service.get_creative_insight(db, creative_id, user_org_ids=[orgs[1]])
    assert denied.total == 0 and denied.items == []
    assert len(statements) == 6
    assert all("LIMIT" in statement and "ORDER BY" in statement for statement in statements if "count(" not in statement.lower())


@pytest.mark.asyncio
async def test_playbook_listing_is_bounded_and_user_filtered(corpus):
    db, users, orgs, jobs, suffix, statements = corpus
    first = await playbook_service.list_user_playbooks(db, users[0])
    second = await playbook_service.list_user_playbooks(db, users[0], page=2)
    assert len(first) == 20 and len(second) == 5
    assert all(item["id"].startswith(f"b_{suffix}_0_") for item in first + second)
    assert set(item["id"] for item in first).isdisjoint(item["id"] for item in second)
    assert len(statements) == 2
    assert all("LIMIT" in statement and "ORDER BY" in statement and "playbooks.user_id" in statement for statement in statements)


@pytest.mark.asyncio
async def test_explain_actual_scoped_pages_has_bounded_output(corpus):
    db, users, orgs, jobs, suffix, statements = corpus
    connection = await db.connection()
    captured = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT") and "LIMIT" in statement:
            captured.append((statement, parameters))

    event.listen(connection.sync_connection, "before_cursor_execute", capture)
    try:
        await creative_service.list_brands(db, page=2, page_size=7, user_org_ids=[orgs[0]])
        await analysis_service.list_insights(db, page=2, page_size=7, user_org_ids=[orgs[0]])
        await creative_service.list_creatives(db, page=2, page_size=7, user_org_ids=[orgs[0]])
        with patch.object(settings, "USE_MOCKS", False):
            await discover_service.list_recent_jobs(db, users[0], page_size=7)
        await playbook_service.list_user_playbooks(db, users[0], page=2, page_size=7)
    finally:
        event.remove(connection.sync_connection, "before_cursor_execute", capture)
    assert len(captured) == 5
    for name, expected_rows, (statement, parameters) in zip(
        ("brands", "insights", "creatives", "recent_jobs", "playbooks"), (7, 7, 7, 1, 7), captured
    ):
        result = await connection.exec_driver_sql("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + statement, parameters)
        plan = result.scalar_one()[0]
        assert plan["Plan"]["Node Type"] == "Limit"
        assert plan["Plan"]["Actual Rows"] == expected_rows
        print(f"W3 EXPLAIN {name}: rows={plan['Plan']['Actual Rows']}, shared_hits={plan['Plan']['Shared Hit Blocks']}, execution_ms={plan['Execution Time']}")
        print(f"W3 EXPLAIN PLAN {name}: {json.dumps(plan, sort_keys=True)}")


@pytest.mark.asyncio
async def test_entitlement_already_precedes_discovery_cache(corpus):
    db, users, orgs, jobs, suffix, statements = corpus
    denied = HTTPException(status_code=403, detail="test entitlement denied")
    org = await db.get(Organization, orgs[0])
    statements.clear()
    with patch.object(discover_service, "get_or_create_default_org", new=AsyncMock(return_value=org)), \
         patch.object(discover_service, "translate_search_query", new=AsyncMock(return_value="test")), \
         patch.object(discover_service, "assert_can_spend", new=AsyncMock(side_effect=denied)):
        with pytest.raises(HTTPException) as error:
            await discover_service.trigger_search(db, SearchParams(query="test"), users[0])
    assert error.value.status_code == 403
    assert not any("FROM scrape_jobs" in statement for statement in statements)


@pytest.mark.asyncio
@pytest.mark.parametrize("page_size", [101, 10**100])
async def test_oversized_positive_page_size_is_capped_for_every_service(corpus, page_size):
    db, users, orgs, jobs, suffix, statements = corpus
    connection = await db.connection()
    bounds = []

    def capture_bounds(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT") and "LIMIT" in statement:
            # Inspect executed values, not compiled.statement's original literals:
            # SQLAlchemy reuses that statement for later pagination parameters.
            limit_position = int(re.search(r"LIMIT \$(\d+)", statement).group(1)) - 1
            offset_position = int(re.search(r"OFFSET \$(\d+)", statement).group(1)) - 1
            bounds.append((parameters[limit_position], parameters[offset_position]))

    event.listen(connection.sync_connection, "before_cursor_execute", capture_bounds)
    try:
        with patch.object(settings, "USE_MOCKS", False), \
             patch("app.services.billing_service.check_quota_and_feature", new=AsyncMock()):
            pages = [
                await creative_service.list_creatives(db, page=2, page_size=page_size, user_org_ids=[orgs[0]]),
                await creative_service.list_brands(db, page=2, page_size=page_size, user_org_ids=[orgs[0]]),
                await creative_service.list_patterns(db, page=2, page_size=page_size, user_org_ids=[orgs[0]]),
                await creative_service.list_saved_creatives(db, User(id=users[0]), page=2, page_size=page_size),
                await analysis_service.list_insights(db, page=2, page_size=page_size, user_org_ids=[orgs[0]]),
                await discover_service.list_recent_jobs(db, users[0], page=2, page_size=page_size),
                await analysis_service.get_creative_insight(db, f"c_{suffix}_0_000", page=2, page_size=page_size),
            ]
            playbooks = await playbook_service.list_user_playbooks(db, users[0], page=2, page_size=page_size)
    finally:
        event.remove(connection.sync_connection, "before_cursor_execute", capture_bounds)
    assert bounds == [(100, 100)] * 8
    assert all(page.page == 2 and page.page_size == 100 and len(page.items) <= 100 for page in pages)
    assert len(pages[0].items) == len(pages[4].items) == 40
    assert playbooks == []


@pytest.mark.asyncio
@pytest.mark.parametrize("page,page_size", [
    (0, 20), (-1, 20), (1, 0), (1, -1), (True, 20), (1, True), (1000002, 1),
    (10002, 10**100), ("garbage", 20), (1, "garbage"), ("2", 20), (1, "100"),
])
async def test_invalid_pagination_is_rejected_before_sql(corpus, page, page_size):
    db, users, orgs, jobs, suffix, statements = corpus
    calls = [
        creative_service.list_creatives(db, page=page, page_size=page_size),
        creative_service.list_brands(db, page=page, page_size=page_size),
        creative_service.list_patterns(db, page=page, page_size=page_size),
        creative_service.list_saved_creatives(db, User(id=users[0]), page=page, page_size=page_size),
        analysis_service.list_insights(db, page=page, page_size=page_size),
        discover_service.list_recent_jobs(db, users[0], page=page, page_size=page_size),
        playbook_service.list_user_playbooks(db, users[0], page=page, page_size=page_size),
        analysis_service.get_creative_insight(db, f"c_{suffix}_0_000", page=page, page_size=page_size),
    ]
    for call in calls:
        with pytest.raises(HTTPException) as error:
            await call
        assert error.value.status_code == 422
    assert statements == []
