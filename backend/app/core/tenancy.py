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
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import literal, select, text, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User


@dataclass(frozen=True)
class TenantContext:
    org_ids: Optional[List[str]]
    user_id: str
    platform_admin: bool = False
    enforce: bool = True
    # Pre-authentication lookup of exactly one account by email (sign-in,
    # sign-up, forgot-password, team invite). Lets the users policy show that
    # one row and nothing else. Always lower-case; empty means none.
    auth_email: str = ""


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
    auth_email: str = "",
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
            auth_email=(auth_email or "").strip().lower(),
        )
    )


def reset_tenant(token) -> None:
    _tenant.reset(token)


@contextmanager
def tenant_scope(
    org_ids: Optional[List[str]],
    user_id: str = "",
    *,
    platform_admin: bool = False,
    enforce: bool = True,
):
    """Bind verified tenant scope for detached work and reset it on exit."""
    token = bind_tenant(
        org_ids,
        user_id,
        platform_admin=platform_admin,
        enforce=enforce,
    )
    try:
        yield current_tenant()
    finally:
        reset_tenant(token)


async def apply_worker_claim_context(db: AsyncSession, worker_id: str) -> None:
    """Enable the table-specific worker claim policies for this transaction."""
    await db.execute(
        text("SELECT set_config('helix.worker_claim', '1', true)")
    )
    await db.execute(
        text("SELECT set_config('helix.worker_id', :worker_id, true)"),
        {"worker_id": worker_id},
    )


async def apply_maintenance_context(db: AsyncSession, boot_id: str) -> None:
    """Enable only the stale-job/expired-lease maintenance RLS policies."""
    await db.execute(
        text("SELECT set_config('helix.maintenance', '1', true)")
    )
    await db.execute(
        text("SELECT set_config('helix.maintenance_boot', :boot_id, true)"),
        {"boot_id": boot_id},
    )


async def apply_monitor_claim_context(db: AsyncSession) -> None:
    """Enable the due-monitor-only scheduler policies for this transaction."""
    await db.execute(
        text("SELECT set_config('helix.monitor_claim', '1', true)")
    )


async def apply_monitor_maintenance_lookup_context(db: AsyncSession, monitor_id: str) -> None:
    """Allow maintenance to look up exactly one monitor row by a trusted id."""
    await db.execute(
        text("SELECT set_config('helix.maintenance', '1', true)")
    )
    await db.execute(
        text("SELECT set_config('helix.maintenance_monitor_id', :monitor_id, true)"),
        {"monitor_id": monitor_id},
    )


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
    from app.core.timing import span

    params = tenant_settings_params(ctx)
    info = getattr(db, "info", None)
    # Skip only when this same open transaction already holds these exact
    # values; the marker is cleared whenever a transaction ends.
    if isinstance(info, dict) and db.in_transaction() and info.get(RLS_APPLIED_KEY) == params:
        return
    with span("rls"):
        await db.execute(TENANT_SETTINGS_SQL, params)
    if isinstance(info, dict):
        info[RLS_APPLIED_KEY] = params


# Session.info key holding the RLS parameters applied in the current
# transaction (set by apply_tenant_context and the after_begin listener).
RLS_APPLIED_KEY = "helix_rls_applied"

# All transaction-local RLS settings in one statement: one round trip per
# application.
TENANT_SETTINGS_SQL = text(
    "SELECT set_config('helix.user_id', :user_id, true),"
    " set_config('helix.org_ids', :org_ids, true),"
    " set_config('helix.platform_admin', :platform_admin, true),"
    " set_config('helix.enforce', :enforce, true),"
    " set_config('helix.auth_email', :auth_email, true)"
)


def tenant_settings_params(ctx: TenantContext) -> dict:
    return {
        "user_id": ctx.user_id or "",
        "org_ids": "" if ctx.platform_admin or ctx.org_ids is None else ",".join(ctx.org_ids),
        "platform_admin": "1" if ctx.platform_admin else "0",
        "enforce": "1" if ctx.enforce else "0",
        "auth_email": ctx.auth_email or "",
    }


@asynccontextmanager
async def tenant_db_scope(
    db: AsyncSession,
    org_ids: Optional[List[str]],
    user_id: str = "",
    *,
    platform_admin: bool = False,
    enforce: bool = True,
    auth_email: str = "",
):
    """Bind a short-lived RLS scope and restore the caller's database context."""
    previous = current_tenant()
    token = bind_tenant(
        org_ids,
        user_id,
        platform_admin=platform_admin,
        enforce=enforce,
        auth_email=auth_email,
    )
    try:
        await apply_tenant_context(db)
        yield current_tenant()
    finally:
        reset_tenant(token)
        await apply_tenant_context(
            db,
            previous or TenantContext([], "", platform_admin=False, enforce=True),
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

    # One round trip: owned organizations first, then memberships, same order
    # and de-duplication as two separate lookups.
    owned = select(Organization.id.label("org_id"), literal(0).label("rank")).where(
        Organization.owner_id == user.id
    )
    member = select(OrganizationMember.org_id.label("org_id"), literal(1).label("rank")).where(
        OrganizationMember.user_id == user.id
    )
    combined = union_all(owned, member).subquery()
    rows = _scalar_rows(
        await db.execute(select(combined.c.org_id).order_by(combined.c.rank, combined.c.org_id))
    )
    return list(dict.fromkeys(rows or []))


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


async def bind_request_lookup(db: AsyncSession, *, user_id: str = "", auth_email: str = "") -> None:
    """Before authentication: allow reading exactly one account.

    ``user_id`` when the caller holds a verified token for that id (bearer
    session, sign-out, password reset). ``auth_email`` for an email lookup
    (sign-in, sign-up, forgot-password). No organization is in scope.
    """
    bind_tenant([], user_id or "", platform_admin=False, enforce=True, auth_email=auth_email)
    await apply_tenant_context(db)


@asynccontextmanager
async def with_auth_email(db: AsyncSession, email: str):
    """Keep the caller's scope and also allow reading the account for one email."""
    ctx = current_tenant() or TenantContext([], "")
    async with tenant_db_scope(
        db,
        ctx.org_ids,
        ctx.user_id,
        platform_admin=ctx.platform_admin,
        enforce=ctx.enforce,
        auth_email=email,
    ):
        yield
