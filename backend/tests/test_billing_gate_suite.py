"""
Billing Gatekeeper Test Suite

Covers the strict server-side spend gatekeepers and trial state helpers:
  - assert_can_spend (credit balance, daily credit limit, feature flags, trial expiry)
  - assert_can_generate_image (media quotas: total cap, daily cap, video cap, trial expiry)
  - is_trial_active / get_trial_days_remaining boundary behavior
  - UTC-midnight daily reset helpers (_utc_midnight, _ensure_daily_reset, _ensure_daily_image_reset)

Zero-network, zero-database: SQLAlchemy statements are routed by target entity to
queued rows so the gating logic runs without a live Postgres.
"""
import asyncio
import datetime
import os
import sys
from unittest import mock

os.environ.setdefault("SECRET_KEY", "helix-test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import HTTPException

from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan
from app.services import billing_service


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows if isinstance(rows, list) else [rows]

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def first(self):
        return self._rows[0] if self._rows else None

    def scalars(self):
        return _FakeScalars(self._rows)


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


class _FrozenNow(datetime.datetime):
    """datetime class that always reports the fixed instant set by freeze_now()."""
    fixed = None

    @classmethod
    def now(cls, tz=None):
        if tz is not None and cls.fixed.tzinfo is None:
            return cls.fixed.replace(tzinfo=tz)
        return cls.fixed


def freeze_now(fixed: datetime.datetime):
    """Replaces billing_service.datetime with a frozen clock for the test."""
    _FrozenNow.fixed = fixed
    fake_module = type("FakeDateTimeModule", (), {
        "datetime": _FrozenNow,
        "timedelta": datetime.timedelta,
        "timezone": datetime.timezone,
    })()
    return mock.patch.object(billing_service, "datetime", fake_module)


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def today_midnight():
    now = utc_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def trial_user(**overrides):
    defaults = dict(
        id="u_trial",
        email="trial@helix.ai",
        password_hash="x",
        role="customer",
        trial_started_at=utc_now() - datetime.timedelta(days=1),
        trial_expires_at=utc_now() + datetime.timedelta(days=6),
    )
    defaults.update(overrides)
    return User(**defaults)


def trial_org(**overrides):
    defaults = dict(
        id="org_trial",
        name="Trial Workspace",
        owner_id="u_trial",
        plan_id="plan_trial_default",
        plan="trial",
        credit_balance=25.0,
        credits_used=0.0,
        daily_credits_used_today=0.0,
        daily_credits_reset_at=today_midnight(),
        images_today_date=utc_now().strftime("%Y-%m-%d"),
        status="active",
    )
    defaults.update(overrides)
    return Organization(**defaults)


def trial_plan(**overrides):
    defaults = dict(
        id="plan_trial_default",
        name="7-Day Free Trial",
        type="trial",
        credit_allowance=50,
        daily_credit_limit=15.0,
        price_per_credit=0.0,
        feature_flags={
            "discover": True,
            "intelligence": True,
            "create": True,
            "performance": True,
            "create_media": True,
        },
    )
    defaults.update(overrides)
    return Plan(**defaults)


def assert_http(exc, status_code, code):
    assert isinstance(exc, HTTPException), f"expected HTTPException, got {exc!r}"
    assert exc.status_code == status_code, f"expected {status_code}, got {exc.status_code}"
    assert exc.detail.get("code") == code, f"expected code {code}, got {exc.detail.get('code')}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_utc_midnight_handles_naive_and_aware():
    naive = datetime.datetime(2026, 9, 2, 14, 30, 0)
    assert billing_service._utc_midnight(naive) == datetime.datetime(2026, 9, 2, 0, 0, 0, tzinfo=datetime.timezone.utc)
    aware = datetime.datetime(2026, 9, 2, 14, 30, 0, tzinfo=datetime.timezone.utc)
    assert billing_service._utc_midnight(aware) == aware.replace(hour=0, minute=0, second=0, microsecond=0)
    print("[PASS] test_utc_midnight_handles_naive_and_aware passed")


def test_format_iso_never_double_suffixes():
    assert billing_service._format_iso(None) is None
    naive = datetime.datetime(2026, 9, 2, 10, 0, 0)
    iso = billing_service._format_iso(naive)
    assert iso.endswith("+00:00")
    assert iso.count("+00:00") == 1
    aw = billing_service._format_iso(datetime.datetime(2026, 9, 2, 10, 0, 0, tzinfo=datetime.timezone.utc))
    assert aw.count("+00:00") == 1
    print("[PASS] test_format_iso_never_double_suffixes passed")


def test_daily_reset_zeroes_stale_counters():
    fixed = datetime.datetime(2026, 9, 2, 14, 30, 0, tzinfo=datetime.timezone.utc)
    with freeze_now(fixed):
        org = trial_org(daily_credits_used_today=9.0, daily_credits_reset_at=fixed - datetime.timedelta(days=1))
        db = FakeSession()
        asyncio.run(billing_service._ensure_daily_reset(db, org))
        assert org.daily_credits_used_today == 0.0
        assert org.daily_credits_reset_at == datetime.datetime(2026, 9, 2, 0, 0, 0, tzinfo=datetime.timezone.utc)
        assert db.flushed >= 1
    print("[PASS] test_daily_reset_zeroes_stale_counters passed")


def test_daily_reset_keeps_fresh_counters():
    fixed = datetime.datetime(2026, 9, 2, 14, 30, 0, tzinfo=datetime.timezone.utc)
    with freeze_now(fixed):
        midnight = fixed.replace(hour=0, minute=0, second=0, microsecond=0)
        org = trial_org(daily_credits_used_today=9.0, daily_credits_reset_at=midnight)
        db = FakeSession()
        asyncio.run(billing_service._ensure_daily_reset(db, org))
        assert org.daily_credits_used_today == 9.0
    print("[PASS] test_daily_reset_keeps_fresh_counters passed")


def test_get_or_create_default_org_creates_trial_workspace():
    db = FakeSession()
    user = trial_user()
    org = asyncio.run(billing_service.get_or_create_default_org(db, user))
    assert org.owner_id == user.id
    assert org.plan == "trial"
    assert org.plan_id == "plan_trial_default"
    assert org.credit_balance == 25.0
    assert org.name == "trial's Workspace"
    assert org.status == "active"
    assert len(db.added) == 1 and db.added[0] is org
    assert db.committed >= 1
    print("[PASS] test_get_or_create_default_org_creates_trial_workspace passed")


def test_get_or_create_default_org_reuses_existing():
    org = trial_org()
    db = FakeSession()
    db.queue(Organization, [org])
    returned = asyncio.run(billing_service.get_or_create_default_org(db, trial_user()))
    assert returned is org
    assert db.added == []
    print("[PASS] test_get_or_create_default_org_reuses_existing passed")


def test_get_or_create_default_org_locks_row_when_requested():
    org = trial_org()
    db = FakeSession()
    db.queue(Organization, [org])
    asyncio.run(billing_service.get_or_create_default_org(db, trial_user(), lock_row=True))
    org_stmt = db.executed[0]
    assert getattr(org_stmt, "_for_update_arg", None) is not None, "expected SELECT ... FOR UPDATE"
    print("[PASS] test_get_or_create_default_org_locks_row_when_requested passed")


def test_assert_can_spend_admin_bypasses_all_checks():
    db = FakeSession()
    db.queue(Organization, [trial_org(daily_credits_reset_at=None)])
    user = trial_user(role="admin", trial_expires_at=None)
    org, plan = asyncio.run(billing_service.assert_can_spend(db, user, required_credits=2.0, feature_name="create"))
    assert plan.id == "plan_admin" and plan.type == "admin"
    assert plan.daily_credit_limit is None
    # Only the org lookup executes; no plan fetch or limit checks for admins.
    assert len(db.executed) == 1
    print("[PASS] test_assert_can_spend_admin_bypasses_all_checks passed")


def test_assert_can_spend_trial_expired_raises_403():
    db = FakeSession()
    org = trial_org()
    db.queue(Organization, [org])
    db.queue(Plan, [trial_plan()])
    user = trial_user(trial_expires_at=utc_now() - datetime.timedelta(days=1))
    try:
        asyncio.run(billing_service.assert_can_spend(db, user, required_credits=1.0))
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert_http(exc, 403, "trial_expired")
        assert org.status == "trial_expired"
    print("[PASS] test_assert_can_spend_trial_expired_raises_403 passed")


def test_assert_can_spend_feature_disabled_raises_403():
    db = FakeSession()
    db.queue(Organization, [trial_org()])
    db.queue(Plan, [trial_plan(feature_flags={"discover": False, "create": True})])
    try:
        asyncio.run(billing_service.assert_can_spend(db, trial_user(), required_credits=1.0, feature_name="discover"))
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert_http(exc, 403, "feature_disabled")
        assert exc.detail["feature"] == "discover"
    print("[PASS] test_assert_can_spend_feature_disabled_raises_403 passed")


def test_assert_can_spend_org_custom_flags_override_plan():
    db = FakeSession()
    org = trial_org(custom_feature_flags={"discover": False})
    db.queue(Organization, [org])
    db.queue(Plan, [trial_plan(feature_flags={"discover": True})])
    try:
        asyncio.run(billing_service.assert_can_spend(db, trial_user(), required_credits=1.0, feature_name="discover"))
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert_http(exc, 403, "feature_disabled")
    print("[PASS] test_assert_can_spend_org_custom_flags_override_plan passed")


def test_assert_can_spend_daily_credit_limit_raises_429():
    db = FakeSession()
    db.queue(Organization, [trial_org(daily_credits_used_today=14.0)])
    db.queue(Plan, [trial_plan(daily_credit_limit=15.0)])
    try:
        asyncio.run(billing_service.assert_can_spend(db, trial_user(), required_credits=2.0))
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert_http(exc, 429, "daily_limit_reached")
        assert exc.detail["daily_used"] == 14.0
    print("[PASS] test_assert_can_spend_daily_credit_limit_raises_429 passed")


def test_assert_can_spend_insufficient_credits_raises_402():
    db = FakeSession()
    org = trial_org(credit_balance=1.0)
    db.queue(Organization, [org])
    db.queue(Plan, [trial_plan(daily_credit_limit=None)])
    try:
        asyncio.run(billing_service.assert_can_spend(db, trial_user(), required_credits=2.0))
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert_http(exc, 402, "insufficient_credits")
        assert org.status == "quota_exhausted"
    print("[PASS] test_assert_can_spend_insufficient_credits_raises_402 passed")


def test_assert_can_spend_allows_spend_within_limits():
    db = FakeSession()
    db.queue(Organization, [trial_org(credit_balance=50.0, daily_credits_used_today=10.0)])
    plan = trial_plan()
    db.queue(Plan, [plan])
    org, returned_plan = asyncio.run(billing_service.assert_can_spend(db, trial_user(), required_credits=2.0, feature_name="create"))
    assert returned_plan is plan
    assert org.status == "active"
    print("[PASS] test_assert_can_spend_allows_spend_within_limits passed")


def test_assert_can_generate_image_admin_bypass():
    org = trial_org(images_generated_today=99.0, images_trial_total=99.0)
    db = FakeSession()
    org_returned, plan = asyncio.run(billing_service.assert_can_generate_image(db, trial_user(role="admin"), org=org))
    assert org_returned is org
    assert plan.id == "plan_admin"
    print("[PASS] test_assert_can_generate_image_admin_bypass passed")


def test_assert_can_generate_image_trial_total_cap_raises_402():
    org = trial_org(images_trial_total=25.0, images_generated_today=1.0)
    db = FakeSession()
    db.queue(Plan, [trial_plan()])
    try:
        asyncio.run(billing_service.assert_can_generate_image(db, trial_user(), org=org))
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert_http(exc, 402, "trial_total_limit")
        assert org.status == "quota_exhausted"
    print("[PASS] test_assert_can_generate_image_trial_total_cap_raises_402 passed")


def test_assert_can_generate_image_daily_cap_raises_402():
    org = trial_org(images_generated_today=5.0, images_trial_total=2.0)
    db = FakeSession()
    db.queue(Plan, [trial_plan()])
    try:
        asyncio.run(billing_service.assert_can_generate_image(db, trial_user(), org=org))
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert_http(exc, 402, "daily_limit")
        assert exc.detail["images_daily_limit"] == billing_service.settings.TRIAL_IMAGES_PER_DAY
    print("[PASS] test_assert_can_generate_image_daily_cap_raises_402 passed")


def test_assert_can_generate_image_video_daily_cap_raises_402():
    org = trial_org(videos_generated_today=3.0, images_generated_today=0.0)
    db = FakeSession()
    db.queue(Plan, [trial_plan()])
    try:
        asyncio.run(billing_service.assert_can_generate_image(db, trial_user(), org=org, media_type="video"))
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert_http(exc, 402, "video_limit_reached")
    print("[PASS] test_assert_can_generate_image_video_daily_cap_raises_402 passed")


def test_assert_can_generate_image_trial_expired_raises_402():
    org = trial_org()
    db = FakeSession()
    db.queue(Plan, [trial_plan()])
    user = trial_user(trial_expires_at=utc_now() - datetime.timedelta(days=2))
    try:
        asyncio.run(billing_service.assert_can_generate_image(db, user, org=org))
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert_http(exc, 402, "trial_expired")
        assert org.status == "trial_expired"
    print("[PASS] test_assert_can_generate_image_trial_expired_raises_402 passed")


def test_assert_can_generate_image_allows_within_limits():
    org = trial_org(images_generated_today=2.0, images_trial_total=5.0)
    db = FakeSession()
    plan = trial_plan()
    db.queue(Plan, [plan])
    returned_org, returned_plan = asyncio.run(billing_service.assert_can_generate_image(db, trial_user(), org=org))
    assert returned_org is org
    assert returned_plan is plan
    print("[PASS] test_assert_can_generate_image_allows_within_limits passed")


def test_is_trial_active_boundaries():
    assert billing_service.is_trial_active(trial_user(role="admin", trial_expires_at=utc_now() - datetime.timedelta(days=9))) is True
    assert billing_service.is_trial_active(trial_user(trial_expires_at=None)) is True
    assert billing_service.is_trial_active(trial_user(trial_expires_at=utc_now() + datetime.timedelta(days=1))) is True
    assert billing_service.is_trial_active(trial_user(trial_expires_at=utc_now() - datetime.timedelta(seconds=1))) is False
    # Naive datetimes are treated as UTC.
    naive_future = datetime.datetime.now() + datetime.timedelta(days=1)
    assert billing_service.is_trial_active(trial_user(trial_expires_at=naive_future)) is True
    print("[PASS] test_is_trial_active_boundaries passed")


def test_get_trial_days_remaining_boundaries():
    assert billing_service.get_trial_days_remaining(trial_user(role="admin")) == 999
    assert billing_service.get_trial_days_remaining(trial_user(trial_expires_at=None)) == billing_service.settings.TRIAL_DAYS
    assert billing_service.get_trial_days_remaining(trial_user(trial_expires_at=utc_now() - datetime.timedelta(hours=1))) == 0
    # 2 days + 5 hours counts as 3 days remaining; exactly 2 days counts as 2.
    assert billing_service.get_trial_days_remaining(trial_user(trial_expires_at=utc_now() + datetime.timedelta(days=2, hours=5))) == 3
    assert billing_service.get_trial_days_remaining(trial_user(trial_expires_at=utc_now() + datetime.timedelta(days=2))) == 2
    print("[PASS] test_get_trial_days_remaining_boundaries passed")


def test_ensure_daily_image_reset_date_boundary():
    fixed = datetime.datetime(2026, 9, 2, 14, 30, 0, tzinfo=datetime.timezone.utc)
    with freeze_now(fixed):
        stale = trial_org(images_today_date="2000-01-01", images_generated_today=7.0, videos_generated_today=2.0)
        db = FakeSession()
        asyncio.run(billing_service._ensure_daily_image_reset(db, stale))
        assert stale.images_generated_today == 0.0
        assert stale.videos_generated_today == 0.0
        assert stale.images_today_date == "2026-09-02"

        fresh = trial_org(images_today_date="2026-09-02", images_generated_today=4.0)
        asyncio.run(billing_service._ensure_daily_image_reset(db, fresh))
        assert fresh.images_generated_today == 4.0
    print("[PASS] test_ensure_daily_image_reset_date_boundary passed")


if __name__ == "__main__":
    print("Running Billing Gatekeeper Test Suite...")
    test_utc_midnight_handles_naive_and_aware()
    test_format_iso_never_double_suffixes()
    test_daily_reset_zeroes_stale_counters()
    test_daily_reset_keeps_fresh_counters()
    test_get_or_create_default_org_creates_trial_workspace()
    test_get_or_create_default_org_reuses_existing()
    test_get_or_create_default_org_locks_row_when_requested()
    test_assert_can_spend_admin_bypasses_all_checks()
    test_assert_can_spend_trial_expired_raises_403()
    test_assert_can_spend_feature_disabled_raises_403()
    test_assert_can_spend_org_custom_flags_override_plan()
    test_assert_can_spend_daily_credit_limit_raises_429()
    test_assert_can_spend_insufficient_credits_raises_402()
    test_assert_can_spend_allows_spend_within_limits()
    test_assert_can_generate_image_admin_bypass()
    test_assert_can_generate_image_trial_total_cap_raises_402()
    test_assert_can_generate_image_daily_cap_raises_402()
    test_assert_can_generate_image_video_daily_cap_raises_402()
    test_assert_can_generate_image_trial_expired_raises_402()
    test_assert_can_generate_image_allows_within_limits()
    test_is_trial_active_boundaries()
    test_get_trial_days_remaining_boundaries()
    test_ensure_daily_image_reset_date_boundary()
    print("\n=======================================================")
    print("ALL 23 BILLING GATEKEEPER SUITE TESTS PASSED (100% SUCCESS)")
    print("=======================================================")
