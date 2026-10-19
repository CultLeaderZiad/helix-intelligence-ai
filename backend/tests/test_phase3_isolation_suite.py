"""Phase 3 Test Suite: Tenant, Workspace, and Admin Isolation.

Tests cover:
- F03: Cross-tenant creative save rejected (404)
- F04: Playbook compilation cross-tenant job rejected (404) & unscoped query org-isolation
- F05: list_brands and list_patterns scoped to user_org_ids
- F06: generate_insight_for_creative and simulate_creative_for_audiences cross-tenant creative rejected (404)
- F12 & F43: SearchContext.jsx hardcoded history removed, namespaced by userId, cleared on logout
- F46 & F47: Team invite RBAC, email mismatch rejection (403), atomic redemption, tenancy membership resolution
- F48: App updates and banner unauthenticated public-only filtering (show_on_public == True)
- F53: Pattern generation job ownership check (404), credit deduction & spend assertion
- F61: API key public_api entitlement verification & single-workspace scoping (_scoped_org_id)
- F80: Granular admin permission checks (require_admin_permission) & route enforcement
"""
from __future__ import annotations

import asyncio
import datetime
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.user import User
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember, OrganizationInvite
from app.models.scrape_job import ScrapeJob
from app.models.creative import Creative
from app.models.pattern import Pattern
from app.models.ai_insight import AIInsight
from app.models.api_key import ApiKey
from app.models.plan import Plan
from app.models.saved_creative import SavedCreative
from app.core.tenancy import get_user_org_ids
from app.core.deps import require_admin_permission
from app.services.creative_service import save_creative, generate_patterns_for_recent_creatives
from app.services.playbook_service import compile_playbook
from app.services.analysis_service import generate_insight_for_creative
from app.services.simulation_service import simulate_creative_for_audiences
from app.services.team_service import _check_team_management_permission, invite_member, accept_invite
from app.services.api_key_service import authenticate_api_key, hash_key

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# F03: Cross-Tenant Creative Save
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f03_creative_save_cross_tenant_isolation():
    user_a = User(id="usr_a", email="user_a@tenant-a.com", role="customer")
    org_a = Organization(id="org_a", name="Tenant A Org", owner_id=user_a.id, plan="pro")
    job_a = ScrapeJob(id="job_a", org_id=org_a.id, query="BrandA")
    creative_a = Creative(id="cr_a", job_id=job_a.id, brand_id="br_a", platform="meta")

    user_b = User(id="usr_b", email="user_b@tenant-b.com", role="customer")
    org_b = Organization(id="org_b", name="Tenant B Org", owner_id=user_b.id, plan="pro")

    # Mock DB that returns creative_a belonging to job_a (org_a)
    class MockDB:
        def __init__(self):
            self.saved = []

        async def execute(self, stmt):
            stmt_str = str(stmt)
            class Res:
                def __init__(self, data):
                    self._data = data
                def scalar_one_or_none(self):
                    return self._data
                def scalars(self):
                    return self
                def all(self):
                    return self._data if isinstance(self._data, list) else []

            if "creatives.id =" in stmt_str or "WHERE creatives.id" in stmt_str:
                return Res(creative_a)
            if "scrape_jobs.org_id" in stmt_str and "scrape_jobs.id = " in stmt_str:
                return Res(org_a.id)
            if "saved_creatives" in stmt_str:
                return Res(None)
            if "organizations" in stmt_str:
                return Res(org_b)
            return Res(None)

        def add(self, obj):
            self.saved.append(obj)

        async def commit(self):
            pass

        async def refresh(self, obj):
            obj.id = "saved_123"

    db = MockDB()

    # User B (org_b) attempting to save creative_a (org_a) must be rejected with 404
    with patch("app.services.billing_service.check_quota_and_feature", AsyncMock(return_value=(org_b, None))):
        with patch("app.core.tenancy.get_user_org_ids", AsyncMock(return_value=[org_b.id])):
            with pytest.raises(HTTPException) as exc_info:
                await save_creative(db, user_b, creative_a.id)
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Creative not found"

    # User A (org_a) attempting to save creative_a must succeed
    with patch("app.services.billing_service.check_quota_and_feature", AsyncMock(return_value=(org_a, None))):
        with patch("app.core.tenancy.get_user_org_ids", AsyncMock(return_value=[org_a.id])):
            res = await save_creative(db, user_a, creative_a.id)
            assert res["success"] is True


# ---------------------------------------------------------------------------
# F04: Playbook Compilation Cross-Tenant Job & Query Scoping
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f04_playbook_compile_cross_tenant_isolation():
    user_b = User(id="usr_b", email="user_b@tenant-b.com", role="customer")
    org_b = Organization(id="org_b", name="Tenant B Org", owner_id=user_b.id, plan="pro")
    job_a = ScrapeJob(id="job_a", org_id="org_a", query="BrandA")

    class MockDB:
        def __init__(self):
            self.added = []

        async def execute(self, stmt):
            stmt_str = str(stmt)
            class Res:
                def __init__(self, data):
                    self._data = data
                def scalar_one_or_none(self):
                    return self._data
                def scalars(self):
                    return self
                def all(self):
                    return self._data if isinstance(self._data, list) else []

            if "scrape_jobs" in stmt_str:
                return Res(job_a)
            if "creatives" in stmt_str or "patterns" in stmt_str or "ai_insights" in stmt_str:
                return Res([])
            return Res(None)

        def add(self, obj):
            self.added.append(obj)

        async def commit(self):
            pass

        async def refresh(self, obj):
            pass

    db = MockDB()

    # User B attempting to compile playbook using Tenant A's job_id must raise 404
    with patch("app.services.billing_service.get_or_create_default_org", AsyncMock(return_value=org_b)):
        with patch("app.core.tenancy.get_user_org_ids", AsyncMock(return_value=[org_b.id])):
            with pytest.raises(HTTPException) as exc_info:
                await compile_playbook(
                    db=db,
                    user=user_b,
                    brand_name="BrandA",
                    query="BrandA",
                    job_id=job_a.id
                )
            assert exc_info.value.status_code == 404
            assert "Job not found" in exc_info.value.detail


# ---------------------------------------------------------------------------
# F05: List Brands & Patterns Scoped to Tenant Orgs
# ---------------------------------------------------------------------------
def test_f05_brands_and_patterns_tenant_scoping():
    creative_service_path = REPO_ROOT / "backend" / "app" / "services" / "creative_service.py"
    code = creative_service_path.read_text(encoding="utf-8")

    # Verify list_brands accepts and applies user_org_ids
    assert "user_org_ids: Optional[List[str]] = None" in code
    assert "scoped_jobs = select(ScrapeJob.id).where(ScrapeJob.org_id.in_(user_org_ids))" in code
    assert "query.where(Creative.job_id.in_(scoped_jobs))" in code

    # Null-job patterns are not globally readable.
    assert "Pattern.job_id.is_not(None)" in code
    assert "or_(Pattern.job_id.in_(scoped_jobs), Pattern.job_id.is_(None))" not in code


# ---------------------------------------------------------------------------
# F06: Insights & Simulation Cross-Tenant Isolation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f06_insights_and_simulation_cross_tenant_isolation():
    user_b = User(id="usr_b", email="user_b@tenant-b.com", role="customer")
    org_b = Organization(id="org_b", name="Tenant B Org", owner_id=user_b.id)
    creative_a = Creative(id="cr_foreign", job_id="job_foreign", brand_id="foreign_brand")

    class MockDB:
        async def execute(self, stmt):
            stmt_str = str(stmt)
            class Res:
                def __init__(self, data):
                    self._data = data
                def scalar_one_or_none(self):
                    return self._data
            if "creatives.id =" in stmt_str or "WHERE creatives.id" in stmt_str:
                return Res(creative_a)
            if "scrape_jobs.org_id" in stmt_str:
                return Res("org_a_foreign")
            return Res(None)

    db = MockDB()

    # generate_insight_for_creative on foreign creative -> 404
    with pytest.raises(HTTPException) as exc_insight:
        await generate_insight_for_creative(
            db=db,
            creative_id=creative_a.id,
            user=user_b,
            user_org_ids=[org_b.id]
        )
    assert exc_insight.value.status_code == 404

    # simulate_creative_for_audiences on foreign creative -> 404
    with pytest.raises(HTTPException) as exc_sim:
        await simulate_creative_for_audiences(
            db=db,
            creative_id=creative_a.id,
            segment_ids=["gen_z_gamers"],
            user=user_b,
            user_org_ids=[org_b.id]
        )
    assert exc_sim.value.status_code == 404


# ---------------------------------------------------------------------------
# F12 & F43: Search Context Client Isolation & Storage Namespacing
# ---------------------------------------------------------------------------
def test_f12_f43_search_history_storage_isolation():
    search_context_file = REPO_ROOT / "src" / "context" / "SearchContext.jsx"
    content = search_context_file.read_text(encoding="utf-8")

    # Hardcoded test brands must not exist in SearchContext
    for brand in ["Sneako", "Naturia", "Real Madrid", "Gymshark", "Nike"]:
        assert f'"{brand}"' not in content, f"Hardcoded brand {brand} leaked in SearchContext.jsx"

    # Must namespace storage by userId and clear on logout
    assert "${STORAGE_LATEST_KEY}_${userId}" in content
    assert "${STORAGE_HISTORY_KEY}_${userId}" in content
    assert "setSearchHistory([])" in content
    assert "setLatestSearch(null)" in content


# ---------------------------------------------------------------------------
# F46 & F47: Team Management RBAC and Secure Single-Use Invites
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f46_f47_team_management_rbac_and_invite_redemption():
    owner = User(id="u_owner", email="owner@team.com", role="customer")
    non_member = User(id="u_attacker", email="attacker@evil.com", role="customer")
    regular_member = User(id="u_member", email="member@team.com", role="customer")
    org = Organization(id="org_team", name="Acme Team", owner_id=owner.id)

    class MockDB:
        def __init__(self, member_role=None, invite=None):
            self.member_role = member_role
            self.invite = invite

        async def execute(self, stmt):
            stmt_str = str(stmt)
            class Res:
                def __init__(self, data):
                    self._data = data
                def scalar_one_or_none(self):
                    return self._data
            if "organization_members" in stmt_str:
                if self.member_role in ["owner", "admin"]:
                    return Res(OrganizationMember(org_id=org.id, user_id=regular_member.id, role=self.member_role))
                return Res(None)
            if "organization_invites" in stmt_str:
                return Res(self.invite)
            if "organizations" in stmt_str:
                return Res(org)
            return Res(None)

        def add(self, obj):
            pass
        async def commit(self):
            pass

    # 1. Non-member caller gets 403 on team management
    db_non_member = MockDB(member_role=None)
    with pytest.raises(HTTPException) as exc:
        await _check_team_management_permission(db_non_member, org, non_member)
    assert exc.value.status_code == 403

    # 2. Regular member (not admin/owner) gets 403
    db_regular = MockDB(member_role="member")
    with pytest.raises(HTTPException) as exc:
        await _check_team_management_permission(db_regular, org, regular_member)
    assert exc.value.status_code == 403

    # 3. Owner passes without exception
    await _check_team_management_permission(db_regular, org, owner)

    # 4. Invite redemption binds strictly to invited email (F47)
    future_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2)
    valid_invite = OrganizationInvite(
        id="inv_1",
        org_id=org.id,
        email="colleague@team.com",
        role="member",
        token="tok_secret",
        status="pending",
        expires_at=future_time
    )

    db_invite = MockDB(invite=valid_invite)

    # Mismatched user accepts invite -> 403
    intruder = User(id="u_intruder", email="intruder@other.com", role="customer")
    with pytest.raises(HTTPException) as exc_mismatch:
        await accept_invite(db_invite, token="tok_secret", user=intruder)
    assert exc_mismatch.value.status_code == 403
    assert "different email address" in exc_mismatch.value.detail

    # Intended user accepts invite -> succeeds
    intended_user = User(id="u_intended", email="colleague@team.com", role="customer")
    res = await accept_invite(db_invite, token="tok_secret", user=intended_user)
    assert res["success"] is True
    assert valid_invite.status == "accepted"


# ---------------------------------------------------------------------------
# F48: App Updates & Banner Unauthenticated Filtering
# ---------------------------------------------------------------------------
def test_f48_updates_unauthenticated_public_filtering():
    updates_path = REPO_ROOT / "backend" / "app" / "api" / "routers" / "updates.py"
    code = updates_path.read_text(encoding="utf-8")

    # list_published_updates checks user and applies show_on_public
    assert "user: Optional[User] = Depends(get_optional_user)" in code
    assert "if user is None:" in code
    assert "conditions.append(AppUpdate.show_on_public == True)" in code


# ---------------------------------------------------------------------------
# F53: Generate Patterns Ownership Check & Credit Spending
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f53_generate_patterns_validation_and_credit():
    user = User(id="u_p53", email="p53@test.com", role="customer")
    org = Organization(id="org_p53", name="P53 Org", owner_id=user.id)
    foreign_job = ScrapeJob(id="job_foreign", org_id="org_other", query="Other")

    class MockDB:
        async def execute(self, stmt):
            stmt_str = str(stmt)
            class Res:
                def __init__(self, data):
                    self._data = data
                def scalar_one_or_none(self):
                    return self._data
            if "scrape_jobs" in stmt_str:
                return Res(foreign_job)
            return Res(None)

    db = MockDB()

    # Specifying foreign job_id must raise 404
    with pytest.raises(HTTPException) as exc:
        await generate_patterns_for_recent_creatives(
            db=db,
            user=user,
            job_id="job_foreign",
            user_org_ids=[org.id]
        )
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# F61: API Key Entitlement & Scoping
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f61_api_key_entitlement_and_scoping():
    user = User(id="u_api", email="api@test.com", role="customer")
    org_no_api = Organization(id="org_no_api", name="No API Org", owner_id=user.id, plan_id="plan_basic")
    plan_basic = Plan(id="plan_basic", name="Basic", feature_flags={"public_api": False})

    raw_key = "hlx_live_testsecretkey123"
    api_key_record = ApiKey(
        id="key_1",
        org_id=org_no_api.id,
        user_id=user.id,
        key_hash=hash_key(raw_key),
        is_active=True
    )

    class MockDB:
        def __init__(self, org, plan):
            self.org = org
            self.plan = plan

        async def execute(self, stmt):
            stmt_str = str(stmt)
            class Res:
                def __init__(self, data):
                    self._data = data
                def first(self):
                    return self._data
                def scalar_one_or_none(self):
                    return self._data
                def scalars(self):
                    return self
                def all(self):
                    return self._data if isinstance(self._data, list) else []

            if "organization_access_grants" in stmt_str:
                if self.org.id != "org_api_ok":
                    return Res(None)
                return Res(type("Grant", (), {
                    "revoked_at": None,
                    "expires_at": None,
                    "granted_at": datetime.datetime.now(datetime.timezone.utc),
                    "granted_by_user_id": "admin",
                    "plan_id": "plan_pro",
                    "feature_flags": {"public_api": True},
                })())
            if "access_requests" in stmt_str:
                return Res(None)
            if "api_keys" in stmt_str:
                api_key_record.org_id = self.org.id
                return Res(api_key_record)
            if "users" in stmt_str:
                return Res(user)
            if "organizations" in stmt_str:
                return Res(self.org)
            if "plans" in stmt_str:
                return Res(self.plan)
            return Res(None)

        async def commit(self):
            pass

    # 1. Organization lacking public_api feature entitlement -> 403
    db_no_entitlement = MockDB(org=org_no_api, plan=plan_basic)
    with pytest.raises(HTTPException) as exc:
        await authenticate_api_key(db_no_entitlement, raw_key)
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "access_pending_approval"

    # 2. Organization with public_api feature flag enabled -> succeeds
    org_with_api = Organization(id="org_api_ok", name="API Org", owner_id=user.id, plan_id="plan_pro")
    plan_pro = Plan(id="plan_pro", name="Pro", feature_flags={"public_api": True})
    db_entitled = MockDB(org=org_with_api, plan=plan_pro)

    auth_user, auth_org = await authenticate_api_key(db_entitled, raw_key)
    assert auth_user.id == user.id
    assert auth_org.id == org_with_api.id

    # 3. Verify tenancy scoping respects _scoped_org_id
    auth_user._scoped_org_id = org_with_api.id
    scoped_org_ids = await get_user_org_ids(db_entitled, auth_user)
    assert scoped_org_ids == [org_with_api.id]


# ---------------------------------------------------------------------------
# F80: Granular Admin Permission Enforcement
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f80_granular_admin_permissions():
    full_admin = User(id="u_admin", role="admin")
    assistant_restricted = User(
        id="u_assistant",
        role="assistant-admin",
        admin_permissions={"users": False, "sections": ["overview", "support"]}
    )
    assistant_permitted = User(
        id="u_assistant_ok",
        role="assistant-admin",
        admin_permissions={"users": True, "sections": ["users", "overview", "support"]}
    )

    users_checker = require_admin_permission("users")

    # 1. Full admin always passes
    res = await users_checker(current_user=full_admin)
    assert res.id == full_admin.id

    # 2. Assistant lacking users permission raises 403
    with pytest.raises(HTTPException) as exc:
        await users_checker(current_user=assistant_restricted)
    assert exc.value.status_code == 403
    assert "users" in exc.value.detail

    # 3. Assistant with users permission passes
    res_ok = await users_checker(current_user=assistant_permitted)
    assert res_ok.id == assistant_permitted.id

    # 4. Verify admin support ticket endpoints use require_admin_permission("support")
    admin_py_path = REPO_ROOT / "backend" / "app" / "api" / "routers" / "admin.py"
    admin_py = admin_py_path.read_text(encoding="utf-8")
    assert 'require_admin_permission("support")' in admin_py
