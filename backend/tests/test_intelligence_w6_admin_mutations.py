"""PostgreSQL-backed admin/account mutation regressions using synthetic users."""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from PIL import Image
from sqlalchemy import select
from starlette.datastructures import UploadFile

from app.api.routers import account as account_router
from app.api.routers import updates as updates_router
from app.core.config import settings
from app.core.deps import get_current_full_admin, require_admin_permission
from app.core.security import get_password_hash, verify_password
from app.core.tenancy import tenant_scope
from app.db.session import worker_engine, worker_session_maker
from app.models.access_grant import AccessRequest, OrganizationAccessGrant
from app.models.app_update import AppUpdate
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.support_ticket import SupportTicket, SupportTicketReply
from app.models.usage_log import UsageLog
from app.models.user import User
from app.schemas.admin import GrantCreditsRequest
from app.schemas.app_update import AppUpdateCreate, AppUpdateUpdate
from app.services import admin_service, support_service


@pytest.fixture(autouse=True)
def _require_postgres():
    if worker_engine.dialect.name != "postgresql":
        pytest.fail("W6 admin mutation integration tests require disposable PostgreSQL")


def _suffix() -> str:
    return uuid.uuid4().hex[:12]


def _user(suffix: str, label: str, *, role: str = "customer", permissions=None) -> User:
    return User(
        id=f"w6_{label}_{suffix}",
        email=f"w6_{label}_{suffix}@example.test",
        password_hash=get_password_hash("old-password-123"),
        role=role,
        admin_permissions=permissions or {},
        is_platform_admin=role == "admin",
        signup_metadata={"token_version": 1},
    )


def _organization(suffix: str, label: str, owner: User) -> Organization:
    return Organization(
        id=f"w6_org_{label}_{suffix}",
        name=f"W6 {label} workspace",
        owner_id=owner.id,
        plan_id="plan_trial_default",
        plan="custom",
        status="active",
        credit_balance=10.0,
    )


async def _seed_admin_and_owner(db, suffix: str):
    admin = _user(suffix, "admin", role="admin")
    owner = _user(suffix, "owner")
    admin_org = _organization(suffix, "admin", admin)
    owner_org = _organization(suffix, "owner", owner)
    db.add_all([admin, owner])
    await db.flush()
    db.add_all([admin_org, owner_org])
    await db.flush()
    return admin, owner, admin_org, owner_org


@pytest.mark.asyncio
async def test_non_admin_and_cross_tenant_support_mutations_are_denied():
    suffix = _suffix()
    async with worker_session_maker() as db:
        owner_a = _user(suffix, "owner_a")
        owner_b = _user(suffix, "owner_b")
        assistant = _user(suffix, "assistant", role="assistant-admin")
        org_a = _organization(suffix, "a", owner_a)
        org_b = _organization(suffix, "b", owner_b)
        ticket = SupportTicket(
            id=f"w6_ticket_{suffix}",
            user_id=owner_a.id,
            org_id=org_a.id,
            type="feedback",
            subject="Synthetic support case",
            message="No real customer data",
            status="open",
        )
        db.add_all([owner_a, owner_b, assistant])
        await db.flush()
        db.add_all([org_a, org_b])
        await db.flush()
        db.add(ticket)
        await db.commit()

        with pytest.raises(HTTPException) as admin_denied:
            await get_current_full_admin(current_user=owner_b)
        assert admin_denied.value.status_code == 403

        support_gate = require_admin_permission("support")
        with pytest.raises(HTTPException) as support_denied:
            await support_gate(current_user=assistant)
        assert support_denied.value.status_code == 403

        ticket_id, org_a_id, owner_a_id = ticket.id, org_a.id, owner_a.id
        for actor, org_ids, mutation in (
            (owner_b, [org_b.id], lambda: support_service.get_ticket_details(db, ticket_id, owner_b)),
            (owner_b, [org_b.id], lambda: support_service.add_reply(db, ticket_id, owner_b, "cross-tenant reply")),
            (assistant, [], lambda: support_service.get_ticket_details(db, ticket_id, assistant)),
            (assistant, [], lambda: support_service.add_reply(db, ticket_id, assistant, "unauthorized assistant reply")),
        ):
            await db.refresh(actor)
            with tenant_scope(org_ids, actor.id):
                with pytest.raises(HTTPException) as denied:
                    await mutation()
                assert denied.value.status_code in {403, 404}
            await db.rollback()

        with tenant_scope([org_a_id], owner_a_id):
            replies = (
                await db.execute(
                    select(SupportTicketReply).where(SupportTicketReply.ticket_id == ticket_id)
                )
            ).scalars().all()
            assert replies == []
            stored_ticket = (
                await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
            ).scalar_one()
            assert stored_ticket.status == "open"

        permitted_assistant = _user(
            suffix, "support_assistant", role="assistant-admin", permissions={"support": True}
        )
        permitted_assistant_id = permitted_assistant.id
        db.add(permitted_assistant)
        await db.commit()
        reply = await support_service.add_reply(
            db, ticket_id, permitted_assistant, "Authorized synthetic support reply"
        )
        assert reply["is_admin"] is True
        listed = await support_service.list_admin_tickets(db, actor=permitted_assistant)
        assert any(item["id"] == ticket_id for item in listed)
        await support_service.update_ticket_status(
            db, ticket_id, "in_progress", actor=permitted_assistant
        )
        await db.rollback()
        with tenant_scope([org_a_id], owner_a_id):
            saved_reply = (
                await db.execute(
                    select(SupportTicketReply).where(SupportTicketReply.id == reply["id"])
                )
            ).scalar_one()
            stored_ticket = (
                await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
            ).scalar_one()
            assert saved_reply.message == "Authorized synthetic support reply"
            assert saved_reply.user_id == permitted_assistant_id
            assert stored_ticket.status == "in_progress"


@pytest.mark.asyncio
async def test_admin_grants_role_credit_and_user_status_persist_with_audit():
    suffix = _suffix()
    async with worker_session_maker() as db:
        admin, owner, _admin_org, owner_org = await _seed_admin_and_owner(db, suffix)
        target = _user(suffix, "role_target")
        target_org = _organization(suffix, "role_target", target)
        db.add(target)
        await db.flush()
        db.add(target_org)
        await db.commit()

        role_result = await admin_service.update_user_role(
            db, target.id, "assistant-admin", {"support": True}, admin.id,
        )
        assert role_result["role"] == "assistant-admin"
        await db.refresh(target)
        assert target.admin_permissions == {"support": True}

        credit_result = await admin_service.grant_credits(
            db, owner_org.id, GrantCreditsRequest(amount=4.5, reason="synthetic test grant"), admin.id,
        )
        assert credit_result["new_balance"] == pytest.approx(14.5)
        await db.refresh(owner_org)
        assert owner_org.credit_balance == pytest.approx(14.5)

        with pytest.raises(HTTPException) as invalid_credit:
            await admin_service.grant_credits(
                db, owner_org.id, GrantCreditsRequest(amount=-2.0), admin.id,
            )
        assert invalid_credit.value.status_code == 422

        status_result = await admin_service.update_user_status(
            db, owner.id, "suspended", admin.id,
        )
        assert status_result["status"] == "suspended"
        await db.refresh(owner)
        assert owner.is_suspended is True
        assert owner.signup_metadata["token_version"] == 2

        operations = set((await db.execute(
            select(UsageLog.operation).where(
                UsageLog.user_id == admin.id,
                UsageLog.operation.in_([
                    "admin_user_role_updated",
                    "admin_user_status_updated",
                ]),
            )
        )).scalars().all())
        assert operations == {"admin_user_role_updated", "admin_user_status_updated"}
        credit_log = (await db.execute(
            select(UsageLog).where(
                UsageLog.org_id == owner_org.id,
                UsageLog.operation == "grant_credits",
            )
        )).scalar_one()
        assert credit_log.metadata_json["admin_id"] == admin.id
        assert _admin_org.id != owner_org.id


@pytest.mark.asyncio
async def test_access_decisions_are_atomic_and_revoke_is_audited():
    suffix = _suffix()
    async with worker_session_maker() as db:
        admin, owner, _admin_org, owner_org = await _seed_admin_and_owner(db, suffix)
        plan = Plan(
            id=f"w6_access_plan_{suffix}",
            name="Synthetic access test",
            type="custom",
            feature_flags={"discover": True},
            credit_allowance=0,
        )
        approved_request = AccessRequest(
            id=f"w6_approved_{suffix}",
            org_id=owner_org.id,
            user_id=owner.id,
            requested_features=["discover"],
            status="pending",
        )
        rejected_request = AccessRequest(
            id=f"w6_rejected_{suffix}",
            org_id=owner_org.id,
            user_id=owner.id,
            requested_features=["discover"],
            status="pending",
        )
        db.add_all([plan, approved_request, rejected_request])
        await db.commit()

        decision = await admin_service.approve_access_request(
            db,
            admin,
            approved_request.id,
            plan.id,
            {"discover": True},
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            note="synthetic approval",
        )
        assert decision["status"] == "approved"
        saved_request = await db.get(AccessRequest, approved_request.id)
        assert saved_request.status == "approved"
        grant = (
            await db.execute(
                select(OrganizationAccessGrant).where(
                    OrganizationAccessGrant.request_id == approved_request.id
                )
            )
        ).scalar_one()
        assert grant.granted_by_user_id == admin.id
        assert grant.feature_flags == {"discover": True}

        revoked = await admin_service.revoke_organization_access(
            db, admin, owner_org.id, "synthetic revocation",
        )
        assert revoked["status"] == "revoked"
        await db.refresh(grant)
        assert grant.revoked_by_user_id == admin.id
        assert revoked["data_retained"] is True

        rejected = await admin_service.reject_access_request(
            db, admin, rejected_request.id, "synthetic rejection",
        )
        assert rejected["status"] == "rejected"
        await db.refresh(rejected_request)
        assert rejected_request.decided_by_user_id == admin.id

        operations = set((await db.execute(
            select(UsageLog.operation).where(
                UsageLog.user_id == admin.id,
                UsageLog.operation.in_([
                    "access_granted", "access_revoked", "access_request_rejected",
                ]),
            )
        )).scalars().all())
        assert operations == {"access_granted", "access_revoked", "access_request_rejected"}


@pytest.mark.asyncio
async def test_impersonation_and_publishing_are_full_admin_and_audited(monkeypatch):
    suffix = _suffix()
    monkeypatch.setattr(settings, "SECRET_KEY", "w6-test-only-signing-key-not-a-secret")
    async with worker_session_maker() as db:
        admin, owner, _admin_org, _owner_org = await _seed_admin_and_owner(db, suffix)
        assistant = _user(suffix, "assistant", role="assistant-admin")
        db.add(assistant)
        await db.commit()

        with pytest.raises(HTTPException) as denied:
            await get_current_full_admin(current_user=assistant)
        assert denied.value.status_code == 403

        token = await admin_service.impersonate_user(db, owner.id, actor=admin)
        assert token.user_id == owner.id
        assert token.access_token

        update = await updates_router.admin_create_update(
            AppUpdateCreate(
                title=f"W6 synthetic update {suffix}",
                body="Non-production test content",
                is_published=True,
            ),
            db=db,
            admin=admin,
        )
        assert update.is_published is True
        update_id = update.id

        updated = await updates_router.admin_update_update(
            update_id,
            AppUpdateUpdate(is_published=False),
            db=db,
            admin=admin,
        )
        assert updated.is_published is False
        await updates_router.admin_delete_update(update_id, db=db, admin=admin)
        assert await db.get(AppUpdate, update_id) is None

        operations = set((await db.execute(
            select(UsageLog.operation).where(
                UsageLog.user_id == admin.id,
                UsageLog.operation.in_([
                    "admin_impersonation",
                    "admin_update_created",
                    "admin_update_updated",
                    "admin_update_deleted",
                ]),
            )
        )).scalars().all())
        assert operations == {
            "admin_impersonation",
            "admin_update_created",
            "admin_update_updated",
            "admin_update_deleted",
        }


@pytest.mark.asyncio
async def test_profile_avatar_and_password_writes_persist_with_audit(monkeypatch):
    suffix = _suffix()
    async with worker_session_maker() as db:
        user = _user(suffix, "account")
        org = _organization(suffix, "account", user)
        org_id = org.id
        db.add(user)
        await db.flush()
        db.add(org)
        await db.commit()

        updated = await account_router.update_profile(
            account_router.ProfileUpdateRequest(
                full_name="Synthetic Account",
                avatar_url="https://images.example.test/avatar.png",
                current_password="old-password-123",
                new_password="new-password-456",
            ),
            db=db,
            current_user=user,
        )
        assert updated["status"] == "ok"
        await db.refresh(user)
        assert user.full_name == "Synthetic Account"
        assert user.avatar_url == "https://images.example.test/avatar.png"
        assert await verify_password("new-password-456", user.password_hash)
        assert user.signup_metadata["token_version"] == 2

        with pytest.raises(HTTPException) as bad_password:
            await account_router.update_profile(
                account_router.ProfileUpdateRequest(
                    full_name="Must not persist",
                    current_password="incorrect-password",
                    new_password="another-password-789",
                ),
                db=db,
                current_user=user,
            )
        assert bad_password.value.status_code == 400
        await db.rollback()
        await db.refresh(user)
        assert user.full_name == "Synthetic Account"

        image = Image.new("RGB", (16, 16), color=(30, 90, 140))
        image_buffer = io.BytesIO()
        image.save(image_buffer, format="PNG")
        image_buffer.seek(0)

        async def save_avatar_test_double(encoded, mime, ext, user_id):
            assert encoded
            assert mime == "image/png"
            assert Image.open(io.BytesIO(encoded)).format == "PNG"
            assert ext == "png"
            assert user_id == user.id
            return "/uploads/w6-test-avatar.png"

        monkeypatch.setattr(account_router.storage_service, "save_avatar", save_avatar_test_double)
        result = await account_router.upload_avatar(
            UploadFile(filename="avatar.png", file=image_buffer),
            db=db,
            current_user=user,
        )
        assert result["avatar_url"] == "/uploads/w6-test-avatar.png"
        await db.refresh(user)
        assert user.avatar_url == "/uploads/w6-test-avatar.png"

        logs = (await db.execute(
            select(UsageLog).where(
                UsageLog.user_id == user.id,
                UsageLog.org_id == org_id,
                UsageLog.operation.in_(["account_profile_updated", "account_avatar_updated"]),
            )
        )).scalars().all()
        assert {log.operation for log in logs} == {
            "account_profile_updated", "account_avatar_updated",
        }
        profile_log = next(log for log in logs if log.operation == "account_profile_updated")
        assert "password" in profile_log.metadata_json["fields"]
        assert "new-password-456" not in str(profile_log.metadata_json)
