"""A work item redelivered after a crash must not start (and bill) a second run."""

import datetime
import uuid

import pytest
from sqlalchemy import select, func

from app.db.session import async_session_maker
from app.models.monitor import Monitor, MonitorRun
from app.models.organization import Organization
from app.models.user import User
from app.services import monitor_service


async def _seed(suffix: str, existing_run_age_s):
    async with async_session_maker() as db:
        user = User(id=f"u_{suffix}", email=f"redeliver-{suffix}@example.com", password_hash="x", role="member")
        db.add(user)
        await db.flush()
        org = Organization(id=f"o_{suffix}", name="Redeliver", owner_id=user.id, plan="pro")
        db.add(org)
        await db.flush()
        monitor = Monitor(id=f"m_{suffix}", org_id=org.id, user_id=user.id, name="M", query="q")
        monitor.baseline_at = datetime.datetime.now(datetime.timezone.utc)
        db.add(monitor)
        await db.flush()
        if existing_run_age_s is not None:
            db.add(MonitorRun(
                id=f"first_{suffix}", monitor_id=monitor.id, status="running",
                started_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=existing_run_age_s),
            ))
        await db.commit()
    return monitor.id, org.id


@pytest.fixture
def spy(monkeypatch):
    calls = {"charge": 0, "pipeline": 0}

    async def fake_assert(db, user, **_kw):
        org = (await db.execute(select(Organization).where(Organization.owner_id == user.id))).scalar_one()
        return org, None

    async def fake_charge(**_kw):
        calls["charge"] += 1

    async def fake_pipeline(job_id, query, filters):
        calls["pipeline"] += 1

    monkeypatch.setattr(monitor_service, "assert_can_spend", fake_assert)
    monkeypatch.setattr(monitor_service, "charge", fake_charge)
    monkeypatch.setattr("app.services.discover_service.run_discovery_pipeline", fake_pipeline)
    return calls


async def _runs(monitor_id: str) -> int:
    async with async_session_maker() as db:
        return await db.scalar(select(func.count(MonitorRun.id)).where(MonitorRun.monitor_id == monitor_id))


@pytest.mark.asyncio
async def test_redelivery_while_a_run_is_in_flight_does_not_bill_twice(spy):
    suffix = uuid.uuid4().hex[:8]
    monitor_id, _org = await _seed(suffix, existing_run_age_s=30)

    await monitor_service._run_monitor(monitor_id)

    assert spy == {"charge": 0, "pipeline": 0}
    assert await _runs(monitor_id) == 1


@pytest.mark.asyncio
async def test_a_monitor_with_no_run_in_flight_still_runs(spy):
    suffix = uuid.uuid4().hex[:8]
    monitor_id, _org = await _seed(suffix, existing_run_age_s=None)

    await monitor_service._run_monitor(monitor_id)

    assert spy["charge"] == 1 and spy["pipeline"] == 1
    assert await _runs(monitor_id) == 1
