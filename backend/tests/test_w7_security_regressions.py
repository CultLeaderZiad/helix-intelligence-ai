from __future__ import annotations

import datetime
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import FileResponse

from app.api.routers import uploads
from app.api.routers.support import TicketCreateRequest
from app.core import tenancy
from app.core.config import settings
from app.models.api_key import ApiKey
from app.models.organization import Organization
from app.models.organization_member import OrganizationInvite, OrganizationMember
from app.models.user import User
from app.services import admin_service, api_key_service, storage_service, support_service, team_service


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value if isinstance(self.value, list) else ([] if self.value is None else [self.value])


@pytest.mark.asyncio
async def test_removed_member_api_key_is_revoked_and_rejected():
    user = User(id="former-member", email="former@example.test", role="customer")
    org = Organization(id="private-org", name="Private", owner_id="org-owner", status="active")
    key = ApiKey(
        id="former-key",
        org_id=org.id,
        user_id=user.id,
        key_hash=api_key_service.hash_key("hlx_live_former-member"),
        is_active=True,
    )

    class FakeDB:
        commits = 0

        async def execute(self, statement):
            source = str(statement)
            if "api_keys" in source:
                return Result(key)
            if "users" in source:
                return Result(user)
            if "organizations" in source:
                return Result(org)
            if "organization_members" in source:
                return Result(None)
            return Result(None)

        async def commit(self):
            self.commits += 1

    db = FakeDB()
    with pytest.raises(HTTPException) as denied:
        await api_key_service.authenticate_api_key(db, "hlx_live_former-member")

    assert denied.value.status_code == 401
    assert key.is_active is False
    assert db.commits == 1


@pytest.mark.asyncio
async def test_team_removal_revokes_members_api_keys(monkeypatch):
    owner = User(id="team-owner", email="owner@example.test", role="customer")
    member = OrganizationMember(id="membership-1", org_id="team-org", user_id="member-1", role="member")
    org = Organization(id="team-org", name="Team", owner_id=owner.id)
    keys = [
        ApiKey(id="key-1", org_id=org.id, user_id=member.user_id, is_active=True),
        ApiKey(id="other-user-key", org_id=org.id, user_id="other-member", is_active=True),
    ]

    async def get_org(_db, _user):
        return org

    async def allow_manager(_db, _org, _user):
        return None

    monkeypatch.setattr(team_service, "get_or_create_default_org", get_org)
    monkeypatch.setattr(team_service, "_check_team_management_permission", allow_manager)

    class FakeDB:
        deleted = None

        async def execute(self, statement):
            source = str(statement)
            if "organization_members" in source:
                return Result(member)
            if "api_keys" in source:
                return Result(keys)
            return Result(None)

        async def delete(self, value):
            self.deleted = value

        async def commit(self):
            pass

    db = FakeDB()
    await team_service.remove_member(db, owner, member.id)

    assert db.deleted is member
    assert keys[0].is_active is False
    assert keys[1].is_active is True


@pytest.mark.asyncio
async def test_invite_redemption_applies_and_restores_rls_scope(monkeypatch):
    user = User(id="invitee", email="invitee@example.test", role="customer")
    org = Organization(id="invited-org", name="Invited", owner_id="other-user")
    invite = OrganizationInvite(
        id="invite-1",
        org_id=org.id,
        email=user.email,
        role="member",
        token="invite-token",
        status="pending",
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1),
    )
    observed = []

    async def record_scope(_db, context=None):
        observed.append(context or tenancy.current_tenant())

    monkeypatch.setattr(tenancy, "apply_tenant_context", record_scope)

    class FakeDB:
        added = []

        async def execute(self, statement):
            source = str(statement)
            if "organization_invites" in source:
                return Result(invite)
            if "organizations" in source:
                return Result(org)
            if "organization_members" in source:
                return Result(None)
            return Result(None)

        def add(self, value):
            self.added.append(value)

        async def commit(self):
            pass

    original = tenancy.bind_tenant([], user.id)
    try:
        db = FakeDB()
        result = await team_service.accept_invite(db, invite.token, user)
        assert result["success"] is True
        assert tenancy.current_tenant().org_ids == []
        assert any(scope.platform_admin for scope in observed if scope is not None)
        assert any(
            scope.org_ids == [org.id] and not scope.platform_admin
            for scope in observed
            if scope is not None
        )
        assert db.added and isinstance(db.added[0], OrganizationMember)
    finally:
        tenancy.reset_tenant(original)


@pytest.mark.asyncio
async def test_role_demotion_clears_platform_admin_and_impersonation_blocks_privileged_targets():
    target = User(
        id="demoted-admin",
        email="demoted@example.test",
        role="admin",
        is_platform_admin=True,
        admin_permissions={"sections": ["users"]},
    )
    full_admin = User(id="full-admin", email="admin@example.test", role="admin", is_platform_admin=True)
    assistant = User(id="assistant", email="assistant@example.test", role="assistant-admin")

    class FakeDB:
        async def execute(self, _statement):
            return Result(target)

        async def commit(self):
            pass

        async def refresh(self, _value):
            pass

    db = FakeDB()
    await admin_service.update_user_role(db, target.id, "assistant-admin")
    assert target.is_platform_admin is False
    assert target.admin_permissions == {}

    target.is_platform_admin = True
    with pytest.raises(HTTPException) as target_denied:
        await admin_service.impersonate_user(db, target.id, actor=full_admin)
    assert target_denied.value.status_code == 403

    target.is_platform_admin = False
    with pytest.raises(HTTPException) as actor_denied:
        await admin_service.impersonate_user(db, target.id, actor=assistant)
    assert actor_denied.value.status_code == 403


def test_support_ticket_inputs_are_bounded_and_context_secrets_are_redacted():
    with pytest.raises(ValidationError):
        TicketCreateRequest(subject="x" * 201, message="message")
    with pytest.raises(ValidationError):
        TicketCreateRequest(
            subject="subject",
            message="message",
            context_data={"payload": "x" * (16 * 1024)},
        )

    sanitized = support_service._sanitize_context_data({
        "api_key": "secret-value",
        "nested": [{"refresh-token": "token-value", "theme": "dark"}],
    })
    assert sanitized == {
        "api_key": "[REDACTED]",
        "nested": [{"refresh-token": "[REDACTED]", "theme": "dark"}],
    }


@pytest.mark.asyncio
async def test_signed_upload_checks_org_membership_inside_tenant_scope(monkeypatch, tmp_path):
    monkeypatch.setattr(uploads, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "SECRET_KEY", "w7-local-test-signing-key")
    filename = "private-result.png"
    (tmp_path / filename).write_bytes(b"image")
    user = User(
        id="media-member",
        email="member@example.test",
        role="customer",
        signup_metadata={"token_version": 3},
        is_banned=False,
        is_suspended=False,
    )
    org = Organization(id="media-org", name="Media", owner_id="other-owner", status="active")
    member = OrganizationMember(id="membership", org_id=org.id, user_id=user.id, role="member")
    observed = []

    async def record_scope(_db, context=None):
        observed.append(context or tenancy.current_tenant())

    monkeypatch.setattr(tenancy, "apply_tenant_context", record_scope)
    url = storage_service.issue_local_url(
        filename,
        org_id=org.id,
        user_id=user.id,
        token_version="3",
    )
    params = {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}
    request = Request({
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": f"/uploads/{filename}",
        "raw_path": f"/uploads/{filename}".encode(),
        "query_string": urlsplit(url).query.encode(),
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("localhost", 8000),
    })

    class FakeDB:
        membership = member

        async def execute(self, statement):
            source = str(statement)
            if "users" in source:
                return Result(user)
            if "organizations" in source:
                return Result(org)
            if "organization_members" in source:
                return Result(self.membership)
            return Result(None)

    response = await uploads.get_upload(filename, request, db=FakeDB(), **params)
    assert isinstance(response, FileResponse)
    assert any(
        scope.org_ids == [org.id] and scope.user_id == user.id and not scope.platform_admin
        for scope in observed
        if scope is not None
    )

    FakeDB.membership = None
    with pytest.raises(HTTPException) as denied:
        await uploads.get_upload(filename, request, db=FakeDB(), **params)
    assert denied.value.status_code == 404
