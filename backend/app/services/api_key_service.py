import hashlib
import secrets
import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException

from app.models.api_key import ApiKey
from app.models.user import User
from app.models.organization import Organization
from app.services.billing_service import check_quota_and_feature, get_or_create_default_org

def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

async def generate_api_key(
    db: AsyncSession,
    user: User,
    name: str = "Default API Key"
) -> Dict[str, Any]:
    # 1. Check feature flag 'public_api' (0 credits required to generate key)
    org, plan = await check_quota_and_feature(db, user, feature_name="public_api", required_credits=0.0)

    # 2. Generate secret key
    random_part = secrets.token_hex(20) # 40 hex chars
    raw_key = f"hlx_live_{random_part}"
    prefix = f"hlx_live_{random_part[:6]}..."
    key_hashed = hash_key(raw_key)

    api_key_record = ApiKey(
        org_id=org.id,
        user_id=user.id,
        name=name,
        key_hash=key_hashed,
        prefix=prefix,
        is_active=True
    )
    db.add(api_key_record)
    await db.commit()
    await db.refresh(api_key_record)

    return {
        "id": api_key_record.id,
        "name": api_key_record.name,
        "prefix": api_key_record.prefix,
        "api_key": raw_key, # Returned only once on creation
        "created_at": api_key_record.created_at.isoformat() + "Z" if api_key_record.created_at else ""
    }

async def list_api_keys(db: AsyncSession, user: User) -> List[Dict[str, Any]]:
    # Gated by public_api feature flag
    await check_quota_and_feature(db, user, feature_name="public_api", required_credits=0.0)

    org = await get_or_create_default_org(db, user)
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.org_id == org.id, ApiKey.is_active == True)
        .order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()

    return [
        {
            "id": k.id,
            "name": k.name,
            "prefix": k.prefix,
            "is_active": k.is_active,
            "created_at": k.created_at.isoformat() + "Z" if k.created_at else "",
            "last_used_at": k.last_used_at.isoformat() + "Z" if k.last_used_at else None
        }
        for k in keys
    ]

async def revoke_api_key(db: AsyncSession, user: User, key_id: str) -> Dict[str, Any]:
    org = await get_or_create_default_org(db, user)
    key_record = (await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.org_id == org.id)
    )).scalar_one_or_none()

    if not key_record:
        raise HTTPException(status_code=404, detail="API Key not found")

    key_record.is_active = False
    await db.commit()
    return {"success": True, "message": "API key revoked"}

async def authenticate_api_key(db: AsyncSession, raw_key: str) -> Tuple[User, Organization]:
    hashed = hash_key(raw_key)
    result = await db.execute(
        select(ApiKey, User, Organization)
        .join(User, ApiKey.user_id == User.id)
        .join(Organization, ApiKey.org_id == Organization.id)
        .where(ApiKey.key_hash == hashed, ApiKey.is_active == True)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid or revoked API Key")

    api_key, user, org = row
    api_key.last_used_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()

    return user, org
