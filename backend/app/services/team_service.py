import secrets
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException

from app.models.organization_member import OrganizationMember, OrganizationInvite
from app.models.organization import Organization
from app.models.user import User
from app.services.billing_service import check_quota_and_feature, get_or_create_default_org

async def list_team(db: AsyncSession, user: User) -> Dict[str, Any]:
    # 1. Check feature flag 'team_accounts'
    await check_quota_and_feature(db, user, feature_name="team_accounts", required_credits=0.0)

    org = await get_or_create_default_org(db, user)

    # Fetch members
    members_result = await db.execute(
        select(OrganizationMember, User)
        .join(User, OrganizationMember.user_id == User.id)
        .where(OrganizationMember.org_id == org.id)
        .order_by(OrganizationMember.created_at.asc())
    )
    member_rows = members_result.all()

    # Ensure org owner is listed if not in OrganizationMember table
    members = [
        {
            "id": m.id,
            "user_id": u.id,
            "email": u.email,
            "role": m.role,
            "joined_at": m.created_at.isoformat() + "Z" if m.created_at else ""
        }
        for m, u in member_rows
    ]

    # If owner isn't in OrganizationMember yet, include them as owner
    owner_user = (await db.execute(select(User).where(User.id == org.owner_id))).scalar_one_or_none()
    if owner_user and not any(m["user_id"] == owner_user.id for m in members):
        members.insert(0, {
            "id": f"owner_{owner_user.id}",
            "user_id": owner_user.id,
            "email": owner_user.email,
            "role": "owner",
            "joined_at": org.created_at.isoformat() + "Z" if hasattr(org, "created_at") and org.created_at else ""
        })

    # Fetch pending invites
    invites_result = await db.execute(
        select(OrganizationInvite)
        .where(OrganizationInvite.org_id == org.id, OrganizationInvite.status == "pending")
        .order_by(OrganizationInvite.created_at.desc())
    )
    invites = invites_result.scalars().all()

    return {
        "org_id": org.id,
        "org_name": org.name,
        "members": members,
        "invites": [
            {
                "id": inv.id,
                "email": inv.email,
                "role": inv.role,
                "token": inv.token,
                "status": inv.status,
                "created_at": inv.created_at.isoformat() + "Z" if inv.created_at else "",
                "expires_at": inv.expires_at.isoformat() + "Z" if inv.expires_at else ""
            }
            for inv in invites
        ]
    }

async def invite_member(db: AsyncSession, user: User, email: str, role: str = "member") -> Dict[str, Any]:
    # 1. Check feature flag 'team_accounts'
    await check_quota_and_feature(db, user, feature_name="team_accounts", required_credits=0.0)

    org = await get_or_create_default_org(db, user)

    # Check if already member
    existing_user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing_user:
        is_member = (await db.execute(
            select(OrganizationMember).where(OrganizationMember.org_id == org.id, OrganizationMember.user_id == existing_user.id)
        )).scalar_one_or_none()
        if is_member or org.owner_id == existing_user.id:
            raise HTTPException(status_code=400, detail="This user is already a member of the organization")

    # Create invite token
    token = secrets.token_urlsafe(24)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)

    invite = OrganizationInvite(
        org_id=org.id,
        email=email,
        role=role,
        invited_by_user_id=user.id,
        token=token,
        status="pending",
        expires_at=expires_at
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    return {
        "success": True,
        "message": f"Invitation sent to {email}",
        "invite_id": invite.id,
        "token": token
    }

async def cancel_invite(db: AsyncSession, user: User, invite_id: str) -> Dict[str, Any]:
    org = await get_or_create_default_org(db, user)
    invite = (await db.execute(
        select(OrganizationInvite).where(OrganizationInvite.id == invite_id, OrganizationInvite.org_id == org.id)
    )).scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")

    invite.status = "canceled"
    await db.commit()
    return {"success": True, "message": "Invitation canceled"}

async def accept_invite(db: AsyncSession, token: str, user: User) -> Dict[str, Any]:
    invite = (await db.execute(
        select(OrganizationInvite).where(OrganizationInvite.token == token, OrganizationInvite.status == "pending")
    )).scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")

    now = datetime.datetime.now(datetime.timezone.utc)
    if invite.expires_at.tzinfo is None:
        invite_exp = invite.expires_at.replace(tzinfo=datetime.timezone.utc)
    else:
        invite_exp = invite.expires_at

    if now > invite_exp:
        invite.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="Invitation has expired")

    # Add member
    new_member = OrganizationMember(
        org_id=invite.org_id,
        user_id=user.id,
        role=invite.role
    )
    db.add(new_member)
    invite.status = "accepted"
    await db.commit()

    return {"success": True, "message": "Successfully joined organization", "org_id": invite.org_id}
