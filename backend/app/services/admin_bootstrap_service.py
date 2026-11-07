"""First platform admin bootstrap.

A fresh database has no platform admin, so nobody can use the admin API to
grant access. This promotes one explicitly named, existing account and grants
its own workspace the requested features, through the same services the admin
API uses (``update_user_role`` and ``grant_organization_access``), so the
audit trail and grant rows look exactly like an admin action.

Safety:
* The account is chosen by user id only. There is no email lookup, so a
  similar-looking address cannot be promoted by mistake.
* ``verify_target`` reads the Neon branch id from the server itself and
  refuses to continue unless it matches the branch the operator expected.
* Running it again changes nothing: an existing admin is not re-promoted and
  an active grant that already includes every requested feature is kept.
  Features granted earlier are preserved, never switched off.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import tenant_db_scope
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.user import User
from app.services import admin_service
from app.services.admin_service import GRANTABLE_FEATURES
from app.services.billing_service import _latest_grant


class BootstrapError(RuntimeError):
    """Refused: the inputs or the database do not match what was expected."""


@dataclass
class BootstrapPlan:
    user_id: str
    org_id: str
    plan_id: str
    promote: bool
    grant: bool
    current_flags: Dict[str, bool]
    grant_flags: Dict[str, bool]
    applied: bool = False
    grant_id: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "org_id": self.org_id,
            "plan_id": self.plan_id,
            "promote_to_platform_admin": self.promote,
            "new_access_grant": self.grant,
            "flags_before": self.current_flags,
            "flags_after": self.grant_flags if self.grant else self.current_flags,
            "applied": self.applied,
            "grant_id": self.grant_id,
            "notes": self.notes,
        }


async def verify_target(db: AsyncSession, expected_branch: str) -> str:
    """Return the server-reported Neon branch id, or refuse.

    ``expected_branch="local"`` is accepted only when the server is not a Neon
    endpoint (a local or CI Postgres).
    """
    branch = (
        await db.execute(text("SELECT current_setting('neon.branch_id', true)"))
    ).scalar()
    branch = branch or None
    if expected_branch == "local":
        if branch is not None:
            raise BootstrapError(f"expected a local database but connected to Neon branch {branch}")
        return "local"
    if branch != expected_branch:
        raise BootstrapError(
            f"connected to branch {branch or 'unknown'}, expected {expected_branch}; nothing was changed"
        )
    return branch


def _clean_features(features: Iterable[str]) -> List[str]:
    cleaned = sorted({f.strip() for f in features if f and f.strip()})
    if not cleaned:
        raise BootstrapError("name at least one feature to grant")
    unknown = [f for f in cleaned if f not in GRANTABLE_FEATURES]
    if unknown:
        raise BootstrapError(f"not grantable: {', '.join(unknown)}")
    return cleaned


def _active_flags(grant, now: datetime.datetime) -> Dict[str, bool]:
    if grant is None or grant.revoked_at is not None:
        return {}
    expires = grant.expires_at
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=datetime.timezone.utc)
        if expires <= now:
            return {}
    return {k: bool(v) for k, v in (grant.feature_flags or {}).items() if k in GRANTABLE_FEATURES}


async def _resolve_org(db: AsyncSession, user: User, org_id: Optional[str]) -> Organization:
    if org_id:
        org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
        if org is None:
            raise BootstrapError("workspace not found")
        if org.owner_id != user.id:
            raise BootstrapError("that workspace is not owned by this account")
        return org
    owned = (
        await db.execute(select(Organization).where(Organization.owner_id == user.id))
    ).scalars().all()
    if len(owned) != 1:
        raise BootstrapError(
            f"account owns {len(owned)} workspaces; pass --org-id to choose one"
        )
    return owned[0]


async def plan_bootstrap(
    db: AsyncSession,
    user_id: str,
    features: Iterable[str],
    *,
    org_id: Optional[str] = None,
    plan_id: Optional[str] = None,
) -> BootstrapPlan:
    wanted = _clean_features(features)
    async with tenant_db_scope(db, None, user_id, platform_admin=True):
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            raise BootstrapError("no account with that user id")
        if getattr(user, "is_suspended", False) or getattr(user, "is_banned", False):
            raise BootstrapError("account is suspended or banned")
        org = await _resolve_org(db, user, org_id)
        chosen_plan = plan_id or org.plan_id
        if not chosen_plan or (
            await db.execute(select(Plan.id).where(Plan.id == chosen_plan))
        ).scalar_one_or_none() is None:
            raise BootstrapError("plan not found")
        grant = await _latest_grant(db, org.id)
        current = _active_flags(grant, datetime.datetime.now(datetime.timezone.utc))
        merged = {**current, **{f: True for f in wanted}}
        return BootstrapPlan(
            user_id=user.id,
            org_id=org.id,
            plan_id=chosen_plan,
            promote=not (bool(user.is_platform_admin) and user.role == "admin"),
            grant=any(not current.get(f) for f in wanted),
            current_flags=current,
            grant_flags=merged,
        )


async def apply_bootstrap(db: AsyncSession, plan: BootstrapPlan) -> BootstrapPlan:
    async with tenant_db_scope(db, None, plan.user_id, platform_admin=True):
        if plan.promote:
            await admin_service.update_user_role(db, plan.user_id, "admin", actor_id=plan.user_id)
            plan.notes.append("promoted to platform admin")
        else:
            plan.notes.append("already a platform admin")
        if plan.grant:
            actor = (await db.execute(select(User).where(User.id == plan.user_id))).scalar_one()
            granted = await admin_service.grant_organization_access(
                db, actor, plan.org_id, plan.plan_id, plan.grant_flags
            )
            plan.grant_id = granted["id"]
            plan.notes.append("access granted")
        else:
            plan.notes.append("active grant already includes the requested features")
        await admin_service.record_admin_audit_event(
            db,
            plan.user_id,
            "platform_admin_bootstrap",
            {"org_id": plan.org_id, "promoted": plan.promote, "grant_id": plan.grant_id},
            org_id=plan.org_id,
        )
        await db.commit()
    plan.applied = True
    return plan
