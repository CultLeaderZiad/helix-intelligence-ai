"""Tenant isolation helpers.

Every read that crosses an organization boundary must be scoped with these.
Rules:

* API-key organization scope wins before any owner or platform-admin bypass,
* platform admins without an API key may read across tenants,
* everyone else is limited to organizations they own or belong to,
* a denied cross-tenant read returns **404, never 403**, so resource IDs
  cannot be probed for existence.

Organization ids come from the authenticated user and membership rows.
Callers must not trust an org id supplied only by a header or body.
"""
from contextvars import ContextVar
from dataclasses import dataclass
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User


@dataclass(frozen=True)
class TenantContext:
    org_ids: Optional[List[str]]
    user_id: str
    platform_admin: bool = False
    enforce: bool = True


_tenant: ContextVar[Optional[TenantContext]] = ContextVar("helix_tenant", default=None)


def _scalar_rows(result) -> list:
    scalars = getattr(result, "scalars", None)
    if not callable(scalars):
        return []
    rows = scalars()
    all_rows = getattr(rows, "all", None)
    return list(all_rows() or []) if callable(all_rows) else []


def current_tenant() -> Optional[TenantContext]:
    return _tenant.get()


def bind_tenant(
    org_ids: Optional[List[str]],
    user_id: str,
    *,
    platform_admin: bool = False,
    enforce: bool = True,
):
    """Remember the caller's verified organizations for this task.

    ``org_ids is None`` is the platform-admin unrestricted scope. An API-key
    caller always passes a one-element list and ``platform_admin=False``.
    """
    return _tenant.set(
        TenantContext(
            org_ids=list(org_ids) if org_ids is not None else None,
            user_id=user_id or "",
            platform_admin=platform_admin,
            enforce=enforce,
        )
    )


def reset_tenant(token) -> None:
    _tenant.reset(token)


async def apply_tenant_context(db: AsyncSession, ctx: Optional[TenantContext] = None) -> None:
    """Set transaction-local RLS settings on the open session.

    ``set_config(..., true)`` is local to the current transaction, so a
    connection returned to the pool does not keep the previous tenant.
    """
    ctx = ctx if ctx is not None else current_tenant()
    bind = getattr(db, "bind", None)
    dialect = getattr(getattr(bind, "dialect", None), "name", None)
    if dialect != "postgresql" or ctx is None:
        return
    org_ids = "" if ctx.platform_admin or ctx.org_ids is None else ",".join(ctx.org_ids)
    await db.execute(
        text("SELECT set_config('helix.user_id', :user_id, true)"),
        {"user_id": ctx.user_id or ""},
    )
    await db.execute(
        text("SELECT set_config('helix.org_ids', :org_ids, true)"),
        {"org_ids": org_ids},
    )
    await db.execute(
        text("SELECT set_config('helix.platform_admin', :flag, true)"),
        {"flag": "1" if ctx.platform_admin else "0"},
    )
    await db.execute(
        text("SELECT set_config('helix.enforce', :flag, true)"),
        {"flag": "1" if ctx.enforce else "0"},
    )


async def get_user_org_ids(db: AsyncSession, user: User) -> Optional[List[str]]:
    """Organization ids the caller may read.

    Returns ``None`` for admins, meaning "unrestricted" (unless scoped to an API key).
    An empty list is a legitimate answer (a user with no org sees nothing).
    """
    scoped_org_id = getattr(user, "_scoped_org_id", None)
    if scoped_org_id:
        return [scoped_org_id]

    if getattr(user, "role", None) == "admin":
        return None

    from app.models.organization_member import OrganizationMember

    owned_rows = _scalar_rows(await db.execute(select(Organization.id).where(Organization.owner_id == user.id)))
    member_rows = _scalar_rows(
        await db.execute(select(OrganizationMember.org_id).where(OrganizationMember.user_id == user.id))
    )

    org_ids = list(dict.fromkeys(list(owned_rows or []) + list(member_rows or [])))
    return org_ids


async def require_org_manager(db: AsyncSession, org: Organization, user: User) -> None:
    """Owner or organization admin. Regular members cannot change credentials."""
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    scoped = getattr(user, "_scoped_org_id", None)
    if scoped and scoped != org.id:
        raise HTTPException(status_code=404, detail="Organization not found")
    if org.owner_id == user.id and not scoped:
        return
    if org.owner_id == user.id and scoped == org.id:
        return
    from app.models.organization_member import OrganizationMember

    caller_member = (
        await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.org_id == org.id,
                OrganizationMember.user_id == user.id,
                OrganizationMember.role.in_(["owner", "admin"]),
            )
        )
    ).scalar_one_or_none()
    if caller_member is None:
        raise HTTPException(
            status_code=403,
            detail="Only organization owners and administrators can change workspace credentials or settings",
        )


def is_scoped_out(user_org_ids: Optional[List[str]], org_id: Optional[str]) -> bool:
    """True when the caller must NOT be allowed to see this org's data."""
    if user_org_ids is None:
        return False
    return (not org_id) or (org_id not in user_org_ids)
