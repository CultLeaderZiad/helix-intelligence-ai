import asyncio
import os
import sys
import datetime
from fastapi import HTTPException

# Ensure backend directory is on PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan
from app.services.billing_service import (
    is_trial_active,
    get_trial_days_remaining,
    assert_can_generate_image,
    record_image_generated,
    _ensure_daily_image_reset,
)
from app.services.ai.gemini_provider import GeminiProvider
from app.core.config import settings

def test_trial_lifecycle():
    now = datetime.datetime.now(datetime.timezone.utc)
    # A. Active 7-day trial
    user_active = User(
        id="u_active",
        email="trial@example.com",
        trial_started_at=now,
        trial_expires_at=now + datetime.timedelta(days=7),
        role="customer"
    )
    assert is_trial_active(user_active) is True
    assert get_trial_days_remaining(user_active) == 7
    print("[PASS] Test A: Trial starts at signup and reports 7 days remaining")

    # B. Expired trial
    user_expired = User(
        id="u_expired",
        email="expired@example.com",
        trial_started_at=now - datetime.timedelta(days=8),
        trial_expires_at=now - datetime.timedelta(days=1),
        role="customer"
    )
    assert is_trial_active(user_expired) is False
    assert get_trial_days_remaining(user_expired) == 0
    print("[PASS] Test B: Expired trial detected correctly")

def test_gemini_provider_structure():
    # Verify Gemini provider initialization and safety
    provider = GeminiProvider()
    assert hasattr(provider, "generate_image")
    assert hasattr(provider, "model")
    assert provider.image_model == settings.GEMINI_IMAGE_MODEL
    print("[PASS] Test C: GeminiProvider has generate_image and configured model")

def test_trial_gatekeeper_video_blocked():
    now = datetime.datetime.now(datetime.timezone.utc)
    user = User(
        id="u1",
        email="trial_video@example.com",
        trial_started_at=now,
        trial_expires_at=now + datetime.timedelta(days=7),
        role="customer"
    )
    org = Organization(
        id="org1",
        name="Org 1",
        owner_id=user.id,
        plan="trial",
        plan_id="plan_trial_default",
        images_generated_today=0.0,
        images_trial_total=0.0
    )

    # J. Video on trial must be rejected with 402 video_not_allowed
    class MockDB:
        async def execute(self, q):
            class Res:
                def scalar_one_or_none(self):
                    return Plan(id="plan_trial_default", type="trial", name="Trial")
            return Res()
        async def flush(self): pass
        async def commit(self): pass

    db = MockDB()

    try:
        asyncio.run(assert_can_generate_image(db, user, org, media_type="video"))
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 402
        assert e.detail["code"] == "video_not_allowed"
        print("[PASS] Test J: Video request rejected with HTTP 402 (video_not_allowed)")

def test_trial_daily_limit_and_total_cap():
    now = datetime.datetime.now(datetime.timezone.utc)
    user = User(
        id="u2",
        email="trial_limit@example.com",
        trial_started_at=now,
        trial_expires_at=now + datetime.timedelta(days=7),
        role="customer"
    )

    class MockDB:
        async def execute(self, q):
            class Res:
                def scalar_one_or_none(self):
                    return Plan(id="plan_trial_default", type="trial", name="Trial")
            return Res()
        async def flush(self): pass
        async def commit(self): pass

    db = MockDB()

    # D. 4 images used today -> allowed (5th image)
    org_4 = Organization(
        id="org2",
        name="Org 2",
        owner_id=user.id,
        plan="trial",
        plan_id="plan_trial_default",
        images_generated_today=4.0,
        images_today_date=now.strftime("%Y-%m-%d"),
        images_trial_total=4.0
    )
    asyncio.run(assert_can_generate_image(db, user, org_4, media_type="image"))
    print("[PASS] Test D: 5th image generation allowed")

    # E. 5 images used today -> rejected (6th image) with 402 daily_limit
    org_5 = Organization(
        id="org3",
        name="Org 3",
        owner_id=user.id,
        plan="trial",
        plan_id="plan_trial_default",
        images_generated_today=5.0,
        images_today_date=now.strftime("%Y-%m-%d"),
        images_trial_total=5.0
    )
    try:
        asyncio.run(assert_can_generate_image(db, user, org_5, media_type="image"))
        assert False, "Should have raised daily_limit exception"
    except HTTPException as e:
        assert e.status_code == 402
        assert e.detail["code"] == "daily_limit"
        print("[PASS] Test E: 6th image rejected with HTTP 402 (daily_limit)")

    # F. 25 total images cap -> rejected with 402 trial_total_limit
    org_25 = Organization(
        id="org4",
        name="Org 4",
        owner_id=user.id,
        plan="trial",
        plan_id="plan_trial_default",
        images_generated_today=2.0,
        images_today_date=now.strftime("%Y-%m-%d"),
        images_trial_total=25.0
    )
    try:
        asyncio.run(assert_can_generate_image(db, user, org_25, media_type="image"))
        assert False, "Should have raised trial_total_limit exception"
    except HTTPException as e:
        assert e.status_code == 402
        assert e.detail["code"] == "trial_total_limit"
        print("[PASS] Test F: 25-image total cap rejected with HTTP 402 (trial_total_limit)")

def test_admin_and_paid_bypass():
    now = datetime.datetime.now(datetime.timezone.utc)
    admin_user = User(
        id="u_admin",
        email="admin@example.com",
        trial_started_at=now - datetime.timedelta(days=30),
        trial_expires_at=now - datetime.timedelta(days=20),
        role="admin"
    )
    org = Organization(
        id="org_admin",
        name="Admin Org",
        owner_id=admin_user.id,
        plan="trial",
        images_generated_today=100.0,
        images_trial_total=500.0
    )

    class MockDB:
        async def execute(self, q):
            class Res:
                def scalar_one_or_none(self):
                    return Plan(id="plan_admin", type="admin", name="Admin")
            return Res()
        async def flush(self): pass
        async def commit(self): pass

    db = MockDB()

    # Admin bypasses all trial and daily limits
    res_org, res_plan = asyncio.run(assert_can_generate_image(db, admin_user, org, media_type="video"))
    assert res_plan.type == "admin"
    print("[PASS] Test I: Admin bypass works for trial, limits, and video")

if __name__ == "__main__":
    print("Running HELIX Gemini Trial Image Suite Tests...")
    test_trial_lifecycle()
    test_gemini_provider_structure()
    test_trial_gatekeeper_video_blocked()
    test_trial_daily_limit_and_total_cap()
    test_admin_and_paid_bypass()
    print("\n=================================================================")
    print("ALL GEMINI TRIAL IMAGE SUITE TESTS PASSED (100% SUCCESS)")
    print("=================================================================")
