"""W9: limits that a forged IP cannot reset, and Metapi record guardrails.

* Per-email limits on sign-up, sign-in and forgot-password, a global sign-up
  ceiling and a global reset ceiling (429 + Retry-After, code rate_limited).
* Per-account limits on Discover search create and monitor create / run.
* Monitor cadence floor.
* Per-task record clamp, global safety stop, per-workspace monthly cap
  (database-backed, refused before any Metapi call).

The HTTP tests stub the auth service so no database is needed; the record cap
tests use the real counters (``real_provider_budget``).
"""
from __future__ import annotations

import datetime as dt
import types
import uuid

import httpx
import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import delete, text

from app.core import limits
from app.core.config import settings
from app.core.deps import account_rate_limit
from app.services import auth_service, monitor_service, provider_budget


def _client(ip: str = "203.0.113.10"):
    from app.main import app

    transport = httpx.ASGITransport(app=app, client=(ip, 50000))
    return httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
def _ip_limits_off(monkeypatch):
    # These tests exercise the account/email limits, not the per-IP middleware.
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)


# --- the limiter itself -------------------------------------------------------

def test_hits_past_the_limit_return_a_wait_and_other_keys_are_separate():
    assert limits.hit("t", "a@example.com", 2, 60) is None
    assert limits.hit("t", "A@Example.com ", 2, 60) is None  # same email, normalised
    wait = limits.hit("t", "a@example.com", 2, 60)
    assert wait is not None and 1 <= wait <= 61
    assert limits.hit("t", "b@example.com", 2, 60) is None


def test_enforce_raises_429_with_retry_after():
    limits.enforce("t2", "x", 1, 30)
    with pytest.raises(HTTPException) as exc:
        limits.enforce("t2", "x", 1, 30)
    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "rate_limited"
    assert int(exc.value.headers["Retry-After"]) >= 1


def test_the_key_table_stays_bounded(monkeypatch):
    monkeypatch.setattr(limits, "_MAX_KEYS", 100)
    for i in range(1000):
        limits.hit("flood", f"user{i}@example.com", 5, 60)
    assert len(limits._HITS) <= 100


def test_emails_are_not_kept_in_clear_text():
    limits.hit("t3", "secret-person@example.com", 5, 60)
    assert not any("secret-person" in key for key in limits._HITS)


# --- auth routes --------------------------------------------------------------

@pytest.mark.asyncio
async def test_sign_up_is_limited_per_email_even_from_different_ips(monkeypatch):
    async def _taken(_db, _user_in):
        raise auth_service.EmailAlreadyRegistered()

    monkeypatch.setattr(auth_service, "register_user", _taken)
    monkeypatch.setattr(settings, "AUTH_EMAIL_LIMIT", 2)
    body = {"email": f"w9-{uuid.uuid4().hex[:8]}@example.com", "password": "Strong-Pass-123!"}
    codes = []
    for i in range(3):
        async with _client(ip=f"198.51.100.{i + 1}") as c:
            codes.append((await c.post("/api/auth/sign-up", json=body)))
    assert [r.status_code for r in codes] == [202, 202, 429]
    assert codes[-1].json()["detail"]["code"] == "rate_limited"
    assert "Retry-After" in codes[-1].headers


@pytest.mark.asyncio
async def test_sign_up_has_a_global_ceiling(monkeypatch):
    async def _taken(_db, _user_in):
        raise auth_service.EmailAlreadyRegistered()

    monkeypatch.setattr(auth_service, "register_user", _taken)
    monkeypatch.setattr(settings, "SIGN_UP_GLOBAL_LIMIT", 2)
    async with _client() as c:
        codes = [
            (await c.post("/api/auth/sign-up", json={"email": f"w9g-{i}-{uuid.uuid4().hex[:6]}@example.com",
                                                    "password": "Strong-Pass-123!"})).status_code
            for i in range(3)
        ]
    assert codes == [202, 202, 429]


@pytest.mark.asyncio
async def test_sign_in_attempts_are_limited_per_email(monkeypatch):
    async def _wrong(_db, _user_in):
        return None, None

    monkeypatch.setattr(auth_service, "authenticate_user_and_load", _wrong)
    monkeypatch.setattr(settings, "SIGN_IN_EMAIL_LIMIT", 3)
    body = {"email": f"w9-in-{uuid.uuid4().hex[:8]}@example.com", "password": "whatever-123"}
    async with _client() as c:
        codes = [(await c.post("/api/auth/sign-in", json=body)).status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]


@pytest.mark.asyncio
async def test_forgot_password_is_limited_per_email_whether_or_not_it_exists(monkeypatch):
    async def _none(_db, _email):
        return None

    monkeypatch.setattr(auth_service, "request_password_reset", _none)
    monkeypatch.setattr(settings, "AUTH_EMAIL_LIMIT", 2)
    body = {"email": f"w9-fp-{uuid.uuid4().hex[:8]}@example.com"}
    async with _client() as c:
        codes = [(await c.post("/api/auth/forgot-password", json=body)).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


@pytest.mark.asyncio
async def test_invalid_reset_tokens_do_not_exhaust_recovery_for_others(monkeypatch):
    async def _bad_token(_db, _token, _password):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    monkeypatch.setattr(auth_service, "reset_password", _bad_token)
    body = {"token": "x" * 40, "new_password": "Strong-Pass-123!"}
    async with _client() as c:
        codes = [(await c.post("/api/auth/reset-password", json=body)).status_code for _ in range(3)]
    # No shared ceiling: invalid tokens must not lock everyone out of recovery.
    assert codes == [400, 400, 400]


# --- per-account limits -------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("bucket,limit_name,window_name", [
    ("account-search", "ACCOUNT_SEARCH_LIMIT", "ACCOUNT_SEARCH_WINDOW_S"),
    ("account-monitor", "ACCOUNT_MONITOR_LIMIT", "ACCOUNT_MONITOR_WINDOW_S"),
])
async def test_account_limits_key_on_the_user_not_the_ip(monkeypatch, bucket, limit_name, window_name):
    monkeypatch.setattr(settings, limit_name, 2)
    dep = account_rate_limit(bucket, limit_name, window_name)
    alice, bob = types.SimpleNamespace(id="u-alice"), types.SimpleNamespace(id="u-bob")
    await dep(alice)
    await dep(alice)
    with pytest.raises(HTTPException) as exc:
        await dep(alice)
    assert exc.value.status_code == 429
    await dep(bob)  # another account is unaffected


def test_search_and_monitor_routes_carry_the_account_limit():
    from app.api.routers import discover, monitors

    def limited(router):
        out = set()
        for route in router.routes:
            for dep in getattr(route, "dependencies", []):
                if "account_rate_limit" in getattr(dep.dependency, "__qualname__", ""):
                    out.update((m, route.path) for m in route.methods)
        return out

    assert ("POST", "/jobs") in limited(discover.router)
    monitor_routes = limited(monitors.router)
    assert ("POST", "") in monitor_routes and ("POST", "/{monitor_id}/run") in monitor_routes
    assert not any(m == "GET" for m, _ in monitor_routes)


# --- monitors -----------------------------------------------------------------

def test_cadences_faster_than_the_floor_are_refused(monkeypatch):
    monkeypatch.setattr(settings, "MONITOR_MIN_INTERVAL_HOURS", 12)
    with pytest.raises(HTTPException) as exc:
        monitor_service._enforce_cadence_floor("every_6h")
    assert exc.value.status_code == 422 and exc.value.detail["code"] == "cadence_below_floor"
    monitor_service._enforce_cadence_floor("every_12h")
    monitor_service._enforce_cadence_floor("daily")


def test_the_scheduler_never_runs_faster_than_the_floor(monkeypatch):
    monkeypatch.setattr(settings, "MONITOR_MIN_INTERVAL_HOURS", 24)
    assert monitor_service._interval("every_6h") == dt.timedelta(hours=24)
    assert monitor_service._interval("weekly") == dt.timedelta(days=7)


# --- Metapi record guardrails ---------------------------------------------------

def test_each_task_is_clamped_to_the_per_task_cap(monkeypatch):
    monkeypatch.setattr(settings, "METAPI_MAX_RECORDS_PER_TASK", 15)
    assert provider_budget.task_record_count(50) == 15
    assert provider_budget.task_record_count(10) == 10
    assert provider_budget.task_record_count(None) == 15


def test_the_global_safety_stop_lowers_the_budget(monkeypatch):
    monkeypatch.setattr(settings, "METAPI_GLOBAL_SAFETY_STOP", 2500)
    assert provider_budget.global_record_cap(3000) == 2500
    assert provider_budget.global_record_cap(1000) == 1000
    monkeypatch.setattr(settings, "METAPI_GLOBAL_SAFETY_STOP", 0)
    assert provider_budget.global_record_cap(3000) == 3000


def test_a_plan_overrides_the_workspace_default(monkeypatch):
    monkeypatch.setattr(settings, "METAPI_WORKSPACE_MONTHLY_RECORDS", 150)
    assert provider_budget.workspace_record_cap({}) == 150
    assert provider_budget.workspace_record_cap({"records_per_month": 600}) == 600


@pytest.mark.asyncio
async def test_metapi_task_sends_the_clamped_count_and_the_workspace(monkeypatch):
    from app.services import safe_fetch
    from app.services.scraping.metapi_provider import MetapiProvider

    monkeypatch.setattr(settings, "METAPI_MAX_RECORDS_PER_TASK", 15)
    seen = {}

    async def _reserve(provider, records, budget, org_id=None):
        seen.update(provider=provider, records=records, org_id=org_id)
        return False  # refused: no request may be sent

    async def _never(*_a, **_kw):
        raise AssertionError("Metapi was called after the record cap refused")

    monkeypatch.setattr(provider_budget, "reserve_provider_records", _reserve)
    monkeypatch.setattr(safe_fetch, "safe_request_async", _never)
    p = MetapiProvider(None, "org-w9", "user-w9")
    p.metapi_api_key = "test-key-not-real"
    assert await p._run_task({"advertiser_id": "1", "count": 50}) is None
    assert seen == {"provider": "metapi", "records": 15, "org_id": "org-w9"}
    assert p.records_refused is True


@pytest_asyncio.fixture
async def workspace():
    from app.db.session import worker_session_maker
    from app.models.organization import Organization
    from app.models.user import User

    s = uuid.uuid4().hex[:10]
    user_id, org_id = f"w9_u_{s}", f"w9_o_{s}"
    async with worker_session_maker() as db:
        db.add(User(id=user_id, email=f"w9-{s}@example.com", password_hash="x", role="customer"))
        await db.flush()
        db.add(Organization(id=org_id, name="W9 record cap", owner_id=user_id, plan="trial"))
        await db.commit()
    yield org_id
    async with worker_session_maker() as db:
        await db.execute(text("DELETE FROM workspace_daily_usage WHERE org_id = :o"), {"o": org_id})
        await db.execute(delete(Organization).where(Organization.id == org_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.real_provider_budget
async def test_the_workspace_monthly_cap_refuses_without_counting_refusals(monkeypatch, workspace):
    monkeypatch.setattr(settings, "METAPI_WORKSPACE_MONTHLY_RECORDS", 30)
    provider = f"test-{uuid.uuid4().hex[:8]}"
    assert await provider_budget.reserve_provider_records(provider, 15, 1000, org_id=workspace) is True
    assert await provider_budget.reserve_provider_records(provider, 15, 1000, org_id=workspace) is True
    assert await provider_budget.reserve_provider_records(provider, 15, 1000, org_id=workspace) is False

    from app.db.session import async_session_maker

    async with async_session_maker() as db:
        global_used = (await db.execute(text(
            "SELECT records FROM provider_record_budget WHERE provider = :p "
            "AND period_start = date_trunc('month', now() AT TIME ZONE 'utc')::date"
        ), {"p": provider})).scalar_one()
    assert global_used == 30  # the refused task reached neither counter
    from app.db.session import worker_session_maker

    async with worker_session_maker() as db:
        ws_used = (await db.execute(text(
            "SELECT COALESCE(SUM(records), 0) FROM workspace_daily_usage WHERE org_id = :o"
        ), {"o": workspace})).scalar_one()
    assert ws_used == 30


def test_api_docs_are_off_in_production(monkeypatch):
    import importlib

    import app.main as main

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    try:
        reloaded = importlib.reload(main)
        assert reloaded.app.openapi_url is None and reloaded.app.docs_url is None
    finally:
        monkeypatch.setattr(settings, "ENVIRONMENT", "development")
        importlib.reload(main)


# --- client IP behind Render's proxy --------------------------------------------
# Production runs uvicorn with --proxy-headers --forwarded-allow-ips 10.0.0.0/8
# (render.yaml). uvicorn then replaces the peer with the right-most
# X-Forwarded-For entry that is not a trusted proxy: the address Render's proxy
# appended. A client can prepend anything it likes; it is never used.

def _behind_render(monkeypatch, limit=1):
    from fastapi import FastAPI
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    from app.middleware.rate_limit import RateLimitMiddleware

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "")
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT", limit)
    inner = FastAPI()
    inner.add_api_route("/api/auth/sign-in", lambda: {"ok": True}, methods=["POST"])
    inner.add_middleware(RateLimitMiddleware)
    return ProxyHeadersMiddleware(inner, trusted_hosts="10.0.0.0/8")


async def _post(app, xff):
    transport = httpx.ASGITransport(app=app, client=("10.236.26.183", 51880))  # Render's proxy
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        return (await c.post("/api/auth/sign-in", headers={"x-forwarded-for": xff})).status_code


@pytest.mark.asyncio
async def test_two_real_clients_behind_render_get_separate_buckets(monkeypatch):
    from app.middleware import rate_limit

    rate_limit.reset_buckets()
    app = _behind_render(monkeypatch)
    assert await _post(app, "198.51.100.1") == 200
    assert await _post(app, "198.51.100.1") == 429
    assert await _post(app, "198.51.100.2") == 200  # another person is not locked out


@pytest.mark.asyncio
async def test_a_forged_leftmost_forwarded_for_does_not_get_a_new_bucket(monkeypatch):
    from app.middleware import rate_limit

    rate_limit.reset_buckets()
    app = _behind_render(monkeypatch)
    assert await _post(app, "198.51.100.7") == 200
    for forged in ("203.0.113.1", "203.0.113.2", "1.2.3.4"):
        # Render appends the real address; the forged one is on the left.
        assert await _post(app, f"{forged}, 198.51.100.7") == 429


@pytest.mark.asyncio
async def test_the_scheduler_claim_applies_the_floor_to_old_fast_monitors(monkeypatch, workspace):
    """A monitor saved as every_6h before the floor existed is rescheduled at the floor."""
    from app.core.tenancy import apply_monitor_claim_context
    from app.db.session import async_session_maker, worker_session_maker
    from app.models.monitor import Monitor
    from app.models.organization import Organization

    monkeypatch.setattr(settings, "MONITOR_MIN_INTERVAL_HOURS", 24)
    async with worker_session_maker() as db:
        owner = (await db.get(Organization, workspace)).owner_id
        mid = f"w9_m_{uuid.uuid4().hex[:10]}"
        db.add(Monitor(id=mid, org_id=workspace, user_id=owner, name="old fast", query="x",
                       cadence="every_6h", status="active",
                       next_run_at=dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)))
        await db.commit()
    try:
        async with async_session_maker() as db:
            await apply_monitor_claim_context(db)
            claimed = await monitor_service.claim_due_monitors(db, 1)
        assert [r["id"] for r in claimed] == [mid]
        async with worker_session_maker() as db:
            nxt = (await db.get(Monitor, mid)).next_run_at
        assert nxt - dt.datetime.now(dt.timezone.utc) > dt.timedelta(hours=23)
    finally:
        async with worker_session_maker() as db:
            await db.execute(delete(Monitor).where(Monitor.id == mid))
            await db.commit()
