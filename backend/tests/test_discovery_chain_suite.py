"""
Offline functional test for the Discover pipeline: what a job reports and
what it costs, depending on how the ad-source chain answered.

Run:
    cd backend
    ../.venv/bin/python tests/test_discovery_chain_suite.py

Uses an in-memory SQLite DB and a stubbed scraper chain, so it needs no
Postgres, no network and no provider credentials. It exists because the
real pipeline had two failure modes that were invisible in production:

  1. Stage 3 referenced `clean_query`, a name that only exists in
     trigger_search. Any search whose providers DID return ads died with a
     NameError — i.e. success was the only path that crashed, and every
     environment with broken credentials passed it silently.
  2. "No ad source could be reached" was written as `status=succeeded,
     stage=zero_results` and still billed 1.0 credit, so a billing-blocked
     Apify account looked exactly like a brand that does not advertise.
"""
import asyncio
import datetime
import os
import sys
import types

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("USE_MOCKS", "False")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# app.db.session builds a Postgres engine at import time; stub it with an
# in-memory SQLite maker BEFORE anything imports app.services.
engine = create_async_engine("sqlite+aiosqlite://")
Session = async_sessionmaker(engine, expire_on_commit=False)

_stub = types.ModuleType("app.db.session")
_stub.engine = engine
_stub.async_session_maker = Session


async def _get_db():
    async with Session() as session:
        yield session


_stub.get_db = _get_db
sys.modules["app.db.session"] = _stub

import app.models  # noqa: E402,F401  (register every table on Base.metadata)
from app.db.base import Base  # noqa: E402
from app.models.creative import Creative  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.plan import Plan  # noqa: E402
from app.models.scrape_job import ScrapeJob  # noqa: E402
from app.models.usage_log import UsageLog  # noqa: E402
from app.models.user import User  # noqa: E402
from app.schemas.discover import SearchParams  # noqa: E402
from app.services import discover_service  # noqa: E402
from app.services.billing_service import DISCOVER_SEARCH_CREDIT_COST  # noqa: E402
from app.services.scraping.base import RawCreative  # noqa: E402

COST = DISCOVER_SEARCH_CREDIT_COST


class StubChain:
    """Stand-in for AdLibraryProvider with a scriptable outcome ledger."""

    instance = None

    def __init__(self, db=None, org_id=None, user_id=None):
        # A closed/stale session must never reach the chain; assert the fix.
        assert db is None, "AdLibraryProvider must not be handed a dead session"
        StubChain.instance = self
        self.last_provider_used = "none"
        self.sources_tried = []
        self.source_outcomes = {}
        self.calls = []

    @property
    def any_source_answered(self):
        return any(o.get("status") == "answered" for o in self.source_outcomes.values())

    @property
    def failure_reasons(self):
        return [
            f"{name}: {o.get('detail')}" for name, o in self.source_outcomes.items()
            if o.get("status") == "error"
        ]

    async def search(self, query, max_records=15, filters=None, progress_callback=None):
        self.calls.append(query)
        behaviour = StubChain.behaviour
        if behaviour["raises"]:
            raise RuntimeError("chain exploded")
        self.last_provider_used = behaviour["provider"]
        self.sources_tried = list(behaviour["tried"])
        self.source_outcomes = dict(behaviour["outcomes"])
        return list(behaviour["creatives"])


def behaviour(
    creatives=(),
    provider="none",
    tried=(),
    outcomes=None,
    raises=False,
):
    return {"creatives": list(creatives), "provider": provider, "tried": list(tried),
            "outcomes": dict(outcomes or {}), "raises": raises}


def raw(**kw):
    base = dict(
        platform="meta", format="image", brand_name="Nike",
        headline="Just do it", body="Run further with Nike training kit.",
        cta="Shop now", landing_domain="nike.com", landing_url="https://nike.com",
        first_seen="2026-08-01T00:00:00+00:00", last_seen="2026-09-01T00:00:00+00:00",
        days_active=30, variant_count=1, impressions_est=1000, spend_band="mid",
        data_source="metapi", is_estimated=False,
    )
    base.update(kw)
    return RawCreative(**base)


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    now = datetime.datetime.now(datetime.timezone.utc)
    async with Session() as db:
        db.add(Plan(
            id="plan_trial_default", name="7-Day Free Trial", type="trial",
            credit_allowance=50, daily_credit_limit=None, price_per_credit=0.0,
            feature_flags={"discover": True, "ai_insights": True},
        ))
        user = User(
            id="u_discover", email="discover@example.com", password_hash="x",
            full_name="Discover Tester", role="customer",
            trial_started_at=now, trial_expires_at=now + datetime.timedelta(days=7),
        )
        db.add(user)
        db.add(Organization(
            id="o_discover", name="Discover Workspace", owner_id=user.id,
            plan_id="plan_trial_default", plan="trial", credit_balance=10.0,
            credits_used=0.0, daily_credits_used_today=0.0, status="active",
            images_generated_today=0.0, videos_generated_today=0.0,
            images_trial_total=0.0, custom_feature_flags={},
        ))
        await db.commit()
    return user


async def wait_for_job(job_id, timeout=15.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        async with Session() as db:
            job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one()
            if job.status in ("succeeded", "failed"):
                return job
        await asyncio.sleep(0.05)
    raise AssertionError(f"job {job_id} never reached a terminal state")


class StubScrapeGraph:
    async def extract_landing_page(self, url):
        return None


async def run_search_behaviour(b):
    """Trigger a search with a stubbed chain; return (job, org, usage ops)."""
    StubChain.behaviour = b
    async with Session() as db:
        user = (await db.execute(select(User).where(User.id == "u_discover"))).scalar_one()
        job = await discover_service.trigger_search(db, SearchParams(query="nike"), user.id, None)

    # trigger_search spawns the pipeline as a task on this loop; polling here
    # lets it run to a terminal state (the same lifecycle the API exposes).
    finished = await wait_for_job(job.job_id)
    async with Session() as db:
        org = (await db.execute(select(Organization).where(Organization.id == "o_discover"))).scalar_one()
        logs = (await db.execute(
            select(UsageLog).where(UsageLog.org_id == "o_discover").order_by(UsageLog.id)
        )).scalars().all()
        return finished, org, [l.operation for l in logs]


async def reset_balance():
    async with Session() as db:
        org = (await db.execute(select(Organization).where(Organization.id == "o_discover"))).scalar_one()
        org.credit_balance = 10.0
        org.credits_used = 0.0
        org.daily_credits_used_today = 0.0
        # SQLite has no TIMESTAMPTZ, so a stored aware datetime comes back
        # naive and breaks the UTC-midnight comparison in _ensure_daily_reset.
        # Postgres (the real backend) always returns aware values.
        org.daily_credits_reset_at = None
        org.status = "active"
        await db.execute(UsageLog.__table__.delete())
        await db.execute(ScrapeJob.__table__.delete())
        await db.execute(Creative.__table__.delete())
        await db.commit()


async def main():
    user = await seed()
    discover_service.AdLibraryProvider = StubChain

    async def no_patterns(db, user, job_id):
        return None

    discover_service.generate_patterns_for_recent_creatives = no_patterns
    discover_service.ScrapeGraphProvider = StubScrapeGraph  # Stage 2 stays offline

    # --- 1. providers return ads -> job completes and rows are stored -------
    await reset_balance()
    job, org, ops = await run_search_behaviour(behaviour(
        creatives=[
            raw(headline="{{product.brand}}: Just Do It", body="Run further with the new training kit."),
            raw(headline="Marathon week", body="Train with coaches this month."),
        ],
        provider="metapi",
        tried=["Metapi"],
        outcomes={"Metapi": {"status": "answered", "detail": "2 creatives"}},
    ))
    assert job.status == "succeeded", job.status
    assert job.stage == "complete", job.stage
    async with Session() as db:
        saved = (await db.execute(select(Creative).where(Creative.job_id == job.id))).scalars().all()
    assert job.record_count == 2, job.record_count
    assert len(saved) == 2, f"expected 2 creatives stored, got {len(saved)}"
    # Regression: the brand label that resolves {{product.brand}} was built
    # from `clean_query`, a name that only exists in trigger_search — so this
    # whole stage died with NameError whenever a provider actually returned ads.
    assert any("Nike: Just Do It" in (c.headline or "") for c in saved), [c.headline for c in saved]
    assert org.credit_balance == 10.0 - COST, org.credit_balance
    print("[PASS] Test 1: real results are stored, job succeeds, 1 credit is billed")

    # --- 2. every source errored -> failed, and NOT billed -----------------
    await reset_balance()
    job, org, ops = await run_search_behaviour(behaviour(
        tried=["Meta Graph API", "Apify (Facebook Ad Library)"],
        outcomes={
            "Meta Graph API": {"status": "error", "detail": "HTTP 400 subcode 2332002 — app is not authorized for ads_archive"},
            "Apify (Facebook Ad Library)": {"status": "error", "detail": "HTTP 402 — Apify account has no remaining usage credit"},
        },
    ))
    assert job.status == "failed", job.status
    assert job.stage == "providers_unavailable", job.stage
    assert "2332002" in job.error_msg and "402" in job.error_msg, job.error_msg
    assert org.credit_balance == 10.0, f"balance must be restored, got {org.credit_balance}"
    assert "refund_discover_provider_unavailable" in ops, ops
    print("[PASS] Test 2: blocked providers report providers_unavailable and refund the credit")

    # --- 3. nothing configured -> same treatment, different wording --------
    await reset_balance()
    job, org, ops = await run_search_behaviour(behaviour(
        outcomes={
            "Metapi": {"status": "skipped", "detail": "METAPI_API_KEY not configured"},
            "Adyntel": {"status": "skipped", "detail": "ADYNTEL_API_KEY / ADYNTEL_EMAIL not configured"},
            "Meta Graph API": {"status": "skipped", "detail": "META_ACCESS_TOKEN not configured"},
            "Apify (Facebook Ad Library)": {"status": "skipped", "detail": "APIFY_API_TOKEN not configured"},
        },
    ))
    assert job.status == "failed" and job.stage == "providers_unavailable", (job.status, job.stage)
    assert "No ad source is configured" in job.stage_label, job.stage_label
    assert org.credit_balance == 10.0, org.credit_balance
    print("[PASS] Test 3: an unconfigured deployment is never reported as 'no ads found'")

    # --- 4. a source answered with genuinely nothing -> billed, honest label
    await reset_balance()
    job, org, ops = await run_search_behaviour(behaviour(
        tried=["Metapi"],
        outcomes={"Metapi": {"status": "answered", "detail": "search completed, 0 matching ads"}},
    ))
    assert job.status == "succeeded" and job.stage == "zero_results", (job.status, job.stage)
    assert org.credit_balance == 10.0 - COST, "a real search that matched nothing is billable"
    assert not any(o.startswith("refund_") for o in ops), ops
    print("[PASS] Test 4: a real zero-match search stays billed and says so")

    # --- 5. crash after the search -> failed and refunded ------------------
    await reset_balance()
    job, org, ops = await run_search_behaviour(behaviour(raises=True))
    assert job.status == "failed", job.status
    assert "chain exploded" in (job.error_msg or ""), job.error_msg
    assert org.credit_balance == 10.0, org.credit_balance
    assert "refund_discover_pipeline_failed" in ops, ops
    print("[PASS] Test 5: a crashed search refunds instead of silently charging")

    print("\nAll discovery-chain assertions passed.")


if __name__ == "__main__":
    asyncio.run(main())
