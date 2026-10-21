from __future__ import annotations

from typing import Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.usage_log import UsageLog
from app.models.user import User


async def record_account_mutation(
    db: AsyncSession,
    user: User,
    operation: str,
    fields: Sequence[str],
) -> None:
    """Write account changes to the existing log within the user's tenant."""
    org_id = (
        await db.execute(
            select(Organization.id)
            .where(Organization.owner_id == user.id)
            .order_by(Organization.id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if org_id is None:
        org_id = (
            await db.execute(
                select(OrganizationMember.org_id)
                .where(OrganizationMember.user_id == user.id)
                .order_by(OrganizationMember.created_at, OrganizationMember.org_id)
                .limit(1)
            )
        ).scalar_one_or_none()
    if org_id is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "account_audit_context_missing",
                "message": "This account change cannot be saved without a workspace audit context.",
            },
        )

    db.add(UsageLog(
        org_id=org_id,
        user_id=user.id,
        provider="account",
        operation=operation,
        units=1.0,
        cost_usd=0.0,
        credits_deducted=0.0,
        requests_used=0,
        metadata_json={"fields": sorted(set(fields))},
    ))
