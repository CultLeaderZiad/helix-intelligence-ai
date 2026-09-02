"""
Billing Ledger Test Suite

Covers money-movement paths in billing_service:
  - charge: credit deduction, counters, usage logging, quota_exhausted marking
  - refund: credit restoration, counter rollback, status recovery
  - meter_and_deduct: missing-org failure and delegation to charge
  - record_image_generated / record_video_generated: usage counters and daily reset

Zero-network, zero-database: SQLAlchemy statements are routed by target entity to
queued rows so the ledger logic runs without a live Postgres.
"""
import asyncio
import datetime
import os
import sys

os.environ.setdefault("SECRET_KEY", "helix-test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.user import User
from app.models.organization import Organization
from app.models.usage_log import UsageLog
from app.services import billing_service


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeResult:
    def __init__(self, rows):
        self._rows = rows if isinstance(rows, list) else [rows]

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def first(self):
        return self._rows[0] if self._rows else None


class FakeSession:
    """Routes SQLAlchemy statements by their target entity to queued rows."""

    def __init__(self):
        self.results = {}
        self.executed = []
        self.added = []
        self.committed = 0
        self.flushed = 0
        self.refreshed = []

    def queue(self, entity, rows):
        self.results.setdefault(entity.__name__, []).extend(rows)

    def _rows_for(self, stmt):
        try:
            descriptions = stmt.column_descriptions
        except Exception:
            return None
        for d in descriptions:
            entity = d.get("entity")
            if entity is not None and entity.__name__ in self.results and self.results[entity.__name__]:
                return self.results[entity.__name__].pop(0)
        return None

    async def execute(self, stmt):
        self.executed.append(stmt)
        return _FakeResult(self._rows_for(stmt) or [])

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed += 1

    async def flush(self):
        self.flushed += 1

    async def refresh(self, obj):
        self.refreshed.append(obj)


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def make_org(**overrides):
    now = utc_now()
    defaults = dict(
        id="org_1",
        name="Workspace",
        owner_id="u_1",
        plan_id="plan_growth",
        plan="growth",
        credit_balance=20.0,
        credits_used=0.0,
        daily_credits_used_today=0.0,
        daily_credits_reset_at=now.replace(hour=0, minute=0, second=0, microsecond=0),
        images_generated_today=0.0,
        images_trial_total=0.0,
        images_today_date=now.strftime("%Y-%m-%d"),
        status="active",
    )
    defaults.update(overrides)
    return Organization(**defaults)


def last_added_log(db):
    logs = [obj for obj in db.added if isinstance(obj, UsageLog)]
    assert logs, "expected a UsageLog to be added"
    return logs[-1]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_charge_deducts_balance_and_increments_counters():
    org = make_org(credit_balance=20.0)
    db = FakeSession()
    log = asyncio.run(billing_service.charge(
        db, org, user_id="u_1", amount=3.0, provider="groq", operation="discover_search"
    ))
    assert org.credit_balance == 17.0
    assert org.credits_used == 3.0
    assert org.daily_credits_used_today == 3.0
    assert org.status == "active"
    assert log.credits_deducted == 3.0
    assert log.provider == "groq"
    assert log.operation == "discover_search"
    assert db.committed >= 1
    print("[PASS] test_charge_deducts_balance_and_increments_counters passed")


def test_charge_zero_amount_only_logs():
    org = make_org(credit_balance=20.0)
    db = FakeSession()
    asyncio.run(billing_service.charge(
        db, org, user_id="u_1", amount=0.0, provider="groq", operation="discover_search"
    ))
    assert org.credit_balance == 20.0
    assert org.credits_used == 0.0
    log = last_added_log(db)
    assert log.credits_deducted == 0.0
    print("[PASS] test_charge_zero_amount_only_logs passed")


def test_charge_marks_quota_exhausted_at_zero_balance():
    org = make_org(credit_balance=2.5)
    db = FakeSession()
    asyncio.run(billing_service.charge(db, org, user_id="u_1", amount=3.0, provider="gemini", operation="create_image"))
    assert org.credit_balance == 0.0  # floored, never negative
    assert org.status == "quota_exhausted"
    print("[PASS] test_charge_marks_quota_exhausted_at_zero_balance passed")


def test_charge_logs_token_operations_and_metadata():
    org = make_org()
    db = FakeSession()
    asyncio.run(billing_service.charge(
        db, org, user_id="u_1", amount=0.25, provider="openrouter", operation="token_usage",
        units=2.0, cost_usd=0.01, metadata={"model": "llama-3.3-70b"}
    ))
    log = last_added_log(db)
    assert log.tokens_used == 2
    assert log.cost_usd == 0.01
    assert log.metadata_json == {"model": "llama-3.3-70b"}
    print("[PASS] test_charge_logs_token_operations_and_metadata passed")


def test_charge_daily_reset_happens_before_increment():
    # Stale daily counters are zeroed first so a new charge does not stack on yesterday's usage.
    yesterday_midnight = (utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
                          - datetime.timedelta(days=1))
    org = make_org(daily_credits_used_today=12.0, daily_credits_reset_at=yesterday_midnight)
    db = FakeSession()
    asyncio.run(billing_service.charge(db, org, user_id="u_1", amount=2.0, provider="groq", operation="discover_search"))
    assert org.daily_credits_used_today == 2.0
    print("[PASS] test_charge_daily_reset_happens_before_increment passed")


def test_refund_restores_balance_and_counters():
    org = make_org(credit_balance=2.0, credits_used=18.0, daily_credits_used_today=6.0)
    db = FakeSession()
    db.queue(Organization, [org])
    asyncio.run(billing_service.refund(db, org_id=org.id, amount=5.0, reason="job_failed", job_id="job_1"))
    assert org.credit_balance == 7.0
    assert org.credits_used == 13.0
    assert org.daily_credits_used_today == 1.0
    log = last_added_log(db)
    assert log.credits_deducted == -5.0
    assert log.operation == "refund_job_failed"
    assert log.provider == "system"
    print("[PASS] test_refund_restores_balance_and_counters passed")


def test_refund_recovers_status_from_quota_exhausted():
    org = make_org(credit_balance=0.5, status="quota_exhausted")
    db = FakeSession()
    db.queue(Organization, [org])
    asyncio.run(billing_service.refund(db, org_id=org.id, amount=5.0, reason="job_failed"))
    assert org.credit_balance == 5.5
    assert org.status == "active"
    print("[PASS] test_refund_recovers_status_from_quota_exhausted passed")


def test_refund_ignores_nonpositive_amount():
    db = FakeSession()
    asyncio.run(billing_service.refund(db, org_id="org_1", amount=0.0, reason="job_failed"))
    assert db.executed == []
    assert db.added == []
    print("[PASS] test_refund_ignores_nonpositive_amount passed")


def test_refund_missing_org_is_noop():
    db = FakeSession()
    asyncio.run(billing_service.refund(db, org_id="org_missing", amount=3.0, reason="job_failed"))
    assert db.added == []
    print("[PASS] test_refund_missing_org_is_noop passed")


def test_meter_and_deduct_raises_for_missing_org():
    db = FakeSession()
    try:
        asyncio.run(billing_service.meter_and_deduct(
            db, org_id="org_missing", user_id="u_1", provider="groq", operation="discover_search",
            units=1.0, cost_usd=0.0, credits_deducted=1.0
        ))
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "org_missing" in str(exc)
    print("[PASS] test_meter_and_deduct_raises_for_missing_org passed")


def test_meter_and_deduct_delegates_to_charge():
    org = make_org(credit_balance=10.0)
    db = FakeSession()
    db.queue(Organization, [org])
    log = asyncio.run(billing_service.meter_and_deduct(
        db, org_id=org.id, user_id="u_1", provider="gemini", operation="create_image",
        units=1.0, cost_usd=0.02, credits_deducted=2.0, job_id="job_7"
    ))
    assert org.credit_balance == 8.0
    assert log.credits_deducted == 2.0
    assert log.job_id == "job_7"
    print("[PASS] test_meter_and_deduct_delegates_to_charge passed")


def test_record_image_generated_increments_counters():
    org = make_org(images_generated_today=2.0, images_trial_total=4.0)
    db = FakeSession()
    log = asyncio.run(billing_service.record_image_generated(db, User(id="u_1", email="u@helix.ai"), org, job_id="job_8", cost_usd=0.02))
    assert org.images_generated_today == 3.0
    assert org.images_trial_total == 5.0
    assert log.provider == "gemini"
    assert log.operation == "media_generate_image"
    assert log.metadata_json["images_generated_today"] == 3
    assert org in db.refreshed
    print("[PASS] test_record_image_generated_increments_counters passed")


def test_record_video_generated_increments_counters():
    org = make_org(videos_generated_today=1.0)
    db = FakeSession()
    log = asyncio.run(billing_service.record_video_generated(db, User(id="u_1", email="u@helix.ai"), org, job_id="job_9"))
    assert org.videos_generated_today == 2.0
    assert log.provider == "pollinations"
    assert log.operation == "media_generate_video"
    print("[PASS] test_record_video_generated_increments_counters passed")


def test_record_image_resets_stale_daily_counters_first():
    org = make_org(images_today_date="2000-01-01", images_generated_today=7.0, videos_generated_today=3.0, images_trial_total=4.0)
    db = FakeSession()
    asyncio.run(billing_service.record_image_generated(db, User(id="u_1", email="u@helix.ai"), org))
    # Daily counters reset to zero before the new image is counted; the lifetime total is not reset.
    assert org.images_generated_today == 1.0
    assert org.videos_generated_today == 0.0
    assert org.images_trial_total == 5.0
    print("[PASS] test_record_image_resets_stale_daily_counters_first passed")


if __name__ == "__main__":
    print("Running Billing Ledger Test Suite...")
    test_charge_deducts_balance_and_increments_counters()
    test_charge_zero_amount_only_logs()
    test_charge_marks_quota_exhausted_at_zero_balance()
    test_charge_logs_token_operations_and_metadata()
    test_charge_daily_reset_happens_before_increment()
    test_refund_restores_balance_and_counters()
    test_refund_recovers_status_from_quota_exhausted()
    test_refund_ignores_nonpositive_amount()
    test_refund_missing_org_is_noop()
    test_meter_and_deduct_raises_for_missing_org()
    test_meter_and_deduct_delegates_to_charge()
    test_record_image_generated_increments_counters()
    test_record_video_generated_increments_counters()
    test_record_image_resets_stale_daily_counters_first()
    print("\n=======================================================")
    print("ALL 14 BILLING LEDGER SUITE TESTS PASSED (100% SUCCESS)")
    print("=======================================================")
