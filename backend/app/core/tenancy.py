"""Tenant isolation helpers.

Every read that crosses an organization boundary must be scoped with these.
Rules:

* **admins are unrestricted** - they operate cross-tenant by role,
* **everyone else** is limited to organizations they own,
* a denied cross-tenant read returns **404, never 403**, so resource IDs
  cannot be probed for existence.

Used by discovery job lookup, creative list/detail, and insight reads. Any new
cross-tenant read path must call ``get_user_org_ids`` and pass the result into
the service layer.
"""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User


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

    owned_rows = (
        await db.execute(select(Organization.id).where(Organization.owner_id == user.id))
    ).scalars().all()

    member_rows = (
        await db.execute(select(OrganizationMember.org_id).where(OrganizationMember.user_id == user.id))
    ).scalars().all()

    org_ids = list(dict.fromkeys(list(owned_rows or []) + list(member_rows or [])))
    return org_ids


def is_scoped_out(user_org_ids: Optional[List[str]], org_id: Optional[str]) -> bool:
    """True when the caller must NOT be allowed to see this org's data."""
    if user_org_ids is None:
        return False
    return (not org_id) or (org_id not in user_org_ids)
