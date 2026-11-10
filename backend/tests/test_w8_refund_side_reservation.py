"""W8: refunding a search is not blocked by a released pattern-scoring reservation.

A search charges 1 credit (operation discover_job_start). Pattern scoring may
reserve 0.5 more under the same job_id and release it when the AI step fails.
refund() used to take the newest reservation for the job (the pattern one) and
treat any earlier negative usage row as "already refunded", so a later refund
of the search was skipped or only 0.5 came back.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.services import billing_service as billing


async def _org_and_job(s: str):
    async with async_session_maker() as db:
        user = User(id=f"rf_{s}", email=f"w8-refund-{s}@example.com", password_hash="x", role="customer")
        db.add(user)
        await db.flush()
        org = Organization(id=f"rfo_{s}", name="Refund", owner_id=user.id, plan="trial",
                           plan_id="plan_trial_default", credit_balance=10.0, daily_credits_used_today=0.0)
        db.add(org)
        await db.flush()
        db.add(ScrapeJob(id=f"rfj_{s}", org_id=org.id, query="refund test", status="running"))
        await db.commit()
    return user.id, org.id, f"rfj_{s}"


async def _balance(org_id: str):
    async with async_session_maker() as db:
        org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one()
        return round(float(org.credit_balance), 2), round(float(org.daily_credits_used_today), 2)


@pytest.mark.asyncio
async def test_search_refund_after_a_released_pattern_reservation_returns_the_full_credit():
    s = uuid.uuid4().hex[:8]
    user_id, org_id, job_id = await _org_and_job(s)

    async with async_session_maker() as db:
        org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one()
        await billing.charge(db=db, org=org, user_id=user_id, amount=1.0, provider="discover_composite",
                             operation="discover_job_start", units=1.0, cost_usd=0.0, job_id=job_id, metadata={})
    assert await _balance(org_id) == (9.0, 1.0)

    async with async_session_maker() as db:
        org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one()
        reservation = await billing.reserve_credits(
            db, org=org, user_id=user_id, amount=0.5, operation="pattern_synthesis", job_id=job_id,
            idempotency_key=f"pattern_synthesis:{job_id}:{s}", metadata={"job_id": job_id},
        )
        await billing.release_reservation(db, reservation.id, "pattern_provider_failed")
    assert await _balance(org_id) == (9.0, 1.0)

    async with async_session_maker() as db:
        assert await billing.refund(db, org_id, 1.0, "provider_outage", job_id) is True
    assert await _balance(org_id) == (10.0, 0.0)

    async with async_session_maker() as db:
        assert await billing.refund(db, org_id, 1.0, "provider_outage", job_id) is False
    assert await _balance(org_id) == (10.0, 0.0)
