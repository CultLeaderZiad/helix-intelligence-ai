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

def _format_utc_iso(dt: Optional[datetime.datetime]) -> Optional[str]:
    """Properly formats datetime into ISO UTC string without invalid +00:00Z suffix (F69)."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    else:
        dt = dt.astimezone(datetime.timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


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
            "joined_at": _format_utc_iso(m.created_at) or ""
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
            "joined_at": _format_utc_iso(org.created_at) or ""
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
                "created_at": _format_utc_iso(inv.created_at) or "",
                "expires_at": _format_utc_iso(inv.expires_at) or ""
            }
            for inv in invites
        ]
    }

async def _check_team_management_permission(db: AsyncSession, org: Organization, user: User) -> None:
    """Verifies that user is either the organization owner or an admin member."""
    if org.owner_id == user.id:
        return
    caller_member = (await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.org_id == org.id,
            OrganizationMember.user_id == user.id,
            OrganizationMember.role.in_(["owner", "admin"])
        )
    )).scalar_one_or_none()
    if not caller_member:
        raise HTTPException(
            status_code=403,
            detail="Only organization owners and administrators can manage team invitations and members"
        )


INVITE_ROLES = {"member", "admin"}


async def invite_member(db: AsyncSession, user: User, email: str, role: str = "member") -> Dict[str, Any]:
    # 1. Check feature flag 'team_accounts'
    await check_quota_and_feature(db, user, feature_name="team_accounts", required_credits=0.0)
    if role not in INVITE_ROLES:
        raise HTTPException(status_code=422, detail="Invited role must be member or admin")

    org = await get_or_create_default_org(db, user)
    await _check_team_management_permission(db, org, user)

    # Check if already member
    existing_user = (await db.execute(select(User).where(User.email == email.strip().lower()))).scalar_one_or_none()
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
        email=email.strip().lower(),
        role=role,
        invited_by_user_id=user.id,
        token=token,
        status="pending",
        expires_at=expires_at
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    # Send transactional invitation email (F46)
    from app.services.email_service import send_email
    from app.core.config import settings
    import html
    frontend_url = settings.APP_BASE_URL or settings.PUBLIC_APP_BASE_URL
    invite_url = f"{frontend_url}/team/accept?token={token}"
    safe_name = html.escape(org.name or "a workspace")
    email_body = (
        f"Hello,\n\nYou have been invited to join the team '{org.name}' on Helix Intelligence.\n\n"
        f"Open this link to accept the invitation:\n{invite_url}\n\n"
        "This invitation will expire in 7 days.\n"
    )
    html_body = (
        f"<p>Hello,</p><p>You have been invited to join <strong>{safe_name}</strong> on Helix Intelligence.</p>"
        f"<p><a href=\"{html.escape(invite_url, quote=True)}\">Accept invitation</a></p>"
        "<p>This invitation will expire in 7 days.</p>"
    )
    delivery = await send_email(
        to=email,
        subject=f"Invitation to join {org.name} on Helix Intelligence",
        html=html_body,
        text=email_body,
    )
    delivered = bool(delivery and getattr(delivery, "accepted", False))
    if not delivered:
        import logging
        logging.getLogger(__name__).warning(
            "Team invite email was not accepted for %s: %s",
            email,
            getattr(delivery, "error", None),
        )

    return {
        "success": True,
        "email_dispatched": delivered,
        "message": (
            f"Invitation email accepted for {email}" if delivered
            else f"Invitation created for {email}, but email delivery was not accepted"
        ),
        "invite_id": invite.id,
        "token": token,
        "accept_url": invite_url,
    }

async def cancel_invite(db: AsyncSession, user: User, invite_id: str) -> Dict[str, Any]:
    org = await get_or_create_default_org(db, user)
    await _check_team_management_permission(db, org, user)

    invite = (await db.execute(
        select(OrganizationInvite).where(OrganizationInvite.id == invite_id, OrganizationInvite.org_id == org.id)
    )).scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")

    invite.status = "canceled"
    await db.commit()
    return {"success": True, "message": "Invitation canceled"}

async def accept_invite(db: AsyncSession, token: str, user: User) -> Dict[str, Any]:
    # 1. Row-lock invite with FOR UPDATE to prevent concurrent double-acceptance (F47)
    invite = (await db.execute(
        select(OrganizationInvite).where(OrganizationInvite.token == token, OrganizationInvite.status == "pending").with_for_update()
    )).scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")

    # 2. Bind strictly to intended recipient email (F47)
    if invite.email.strip().lower() != user.email.strip().lower():
        raise HTTPException(
            status_code=403,
            detail="This invitation was issued to a different email address. Please sign in with the invited email account."
        )

    now = datetime.datetime.now(datetime.timezone.utc)
    if invite.expires_at.tzinfo is None:
        invite_exp = invite.expires_at.replace(tzinfo=datetime.timezone.utc)
    else:
        invite_exp = invite.expires_at

    if now > invite_exp:
        invite.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="Invitation has expired")

    org = (await db.execute(select(Organization).where(Organization.id == invite.org_id))).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # 3. Check if user is owner or already a member
    if org.owner_id == user.id:
        invite.status = "accepted"
        await db.commit()
        return {"success": True, "message": "You are the owner of this organization", "org_id": invite.org_id}

    existing_member = (await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.org_id == invite.org_id,
            OrganizationMember.user_id == user.id
        )
    )).scalar_one_or_none()

    if existing_member:
        invite.status = "accepted"
        await db.commit()
        return {"success": True, "message": "Already a member of this organization", "org_id": invite.org_id}

    # 4. Atomically insert member and mark invite accepted
    invited_role = invite.role if invite.role in INVITE_ROLES else None
    if invited_role is None:
        raise HTTPException(status_code=422, detail="Invitation role is not allowed")
    new_member = OrganizationMember(
        org_id=invite.org_id,
        user_id=user.id,
        role=invited_role,
    )
    metadata = dict(getattr(user, "signup_metadata", None) or {})
    metadata["active_org_id"] = invite.org_id
    user.signup_metadata = metadata
    db.add(new_member)
    invite.status = "accepted"
    await db.commit()

    return {"success": True, "message": "Successfully joined organization", "org_id": invite.org_id}

async def remove_member(db: AsyncSession, user: User, member_id: str) -> Dict[str, Any]:
    org = await get_or_create_default_org(db, user)
    await _check_team_management_permission(db, org, user)

    member = (await db.execute(
        select(OrganizationMember).where(OrganizationMember.id == member_id, OrganizationMember.org_id == org.id)
    )).scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")

    if member.user_id == user.id or member.user_id == org.owner_id:
        raise HTTPException(status_code=400, detail="Cannot remove the organization owner")

    await db.delete(member)
    await db.commit()
    return {"success": True, "message": "Team member removed successfully"}

