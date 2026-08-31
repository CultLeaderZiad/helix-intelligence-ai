import datetime
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.models.workspace_credential import WorkspaceProviderCredential
from app.services.billing_service import get_or_create_default_org
from app.services.security_service import encrypt_secret, mask_api_key
from app.services.ai.gemini_provider import GeminiProvider
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

class SetApiKeyRequest(BaseModel):
    api_key: str
    credential_mode: Optional[str] = "byok"

class TestKeyRequest(BaseModel):
    api_key: Optional[str] = None

class SetProviderModeRequest(BaseModel):
    credential_mode: str # 'managed' | 'byok'

@router.get("/workspaces/providers")
async def get_workspace_providers(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Retrieve configured AI providers for the user's workspace.
    Returns masked keys only (e.g. ••••••••abcd). Plaintext secrets are NEVER returned.
    """
    org = await get_or_create_default_org(db, user)

    stmt = select(WorkspaceProviderCredential).where(
        WorkspaceProviderCredential.org_id == org.id,
        WorkspaceProviderCredential.provider == "google_gemini"
    )
    result = await db.execute(stmt)
    cred = result.scalar_one_or_none()

    gemini_info = {
        "provider": "google_gemini",
        "name": "Google Gemini",
        "supported_models": [settings.GEMINI_IMAGE_MODEL, "gemini-flash-latest"],
        "default_image_model": settings.GEMINI_IMAGE_MODEL,
        "credential_mode": cred.credential_mode if cred else "managed",
        "is_byok_configured": bool(cred and cred.encrypted_secret),
        "status": cred.status if cred else "connected",
        "masked_key": f"••••••••{cred.key_suffix}" if (cred and cred.key_suffix) else None,
        "last_tested_at": cred.last_tested_at.isoformat() if (cred and cred.last_tested_at) else None,
    }

    return {
        "workspace_id": org.id,
        "workspace_name": org.name,
        "providers": [gemini_info]
    }

@router.post("/workspaces/provider-credentials/google-gemini")
async def save_gemini_credential(
    body: SetApiKeyRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Save and encrypt a customer BYOK Gemini API key for the workspace.
    Runs a lightweight test connection before persisting.
    """
    raw_key = body.api_key.strip()
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key cannot be empty"
        )

    # 1. Test key validity
    test_provider = GeminiProvider(api_key=raw_key)
    try:
        test_res = await test_provider.test_connection()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_gemini_key",
                "message": f"Connection test failed: {str(e)}"
            }
        )

    # 2. Encrypt key at rest
    org = await get_or_create_default_org(db, user)
    encrypted = encrypt_secret(raw_key)
    suffix = raw_key[-4:] if len(raw_key) >= 4 else raw_key

    stmt = select(WorkspaceProviderCredential).where(
        WorkspaceProviderCredential.org_id == org.id,
        WorkspaceProviderCredential.provider == "google_gemini"
    )
    result = await db.execute(stmt)
    cred = result.scalar_one_or_none()

    now = datetime.datetime.now(datetime.timezone.utc)
    if cred:
        cred.encrypted_secret = encrypted
        cred.key_suffix = suffix
        cred.credential_mode = body.credential_mode or "byok"
        cred.status = "connected"
        cred.model = settings.GEMINI_IMAGE_MODEL
        cred.last_tested_at = now
    else:
        cred = WorkspaceProviderCredential(
            org_id=org.id,
            provider="google_gemini",
            encrypted_secret=encrypted,
            key_suffix=suffix,
            credential_mode=body.credential_mode or "byok",
            status="connected",
            model=settings.GEMINI_IMAGE_MODEL,
            last_tested_at=now
        )
        db.add(cred)

    await db.commit()

    return {
        "status": "connected",
        "provider": "google_gemini",
        "credential_mode": cred.credential_mode,
        "masked_key": f"••••••••{suffix}",
        "message": "Gemini API key encrypted and connected successfully"
    }

@router.post("/workspaces/provider-credentials/google-gemini/test")
async def test_gemini_credential(
    body: TestKeyRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Test Gemini API connection using either a provided key or saved BYOK key.
    """
    api_key_to_test = None
    if body.api_key and body.api_key.strip():
        api_key_to_test = body.api_key.strip()
    else:
        org = await get_or_create_default_org(db, user)
        stmt = select(WorkspaceProviderCredential).where(
            WorkspaceProviderCredential.org_id == org.id,
            WorkspaceProviderCredential.provider == "google_gemini"
        )
        result = await db.execute(stmt)
        cred = result.scalar_one_or_none()
        if cred and cred.encrypted_secret:
            from app.services.security_service import decrypt_secret
            api_key_to_test = decrypt_secret(cred.encrypted_secret)

    if not api_key_to_test:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No API key provided or saved for testing"
        )

    test_provider = GeminiProvider(api_key=api_key_to_test)
    try:
        res = await test_provider.test_connection()
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "test_failed",
                "message": str(e)
            }
        )

@router.delete("/workspaces/provider-credentials/google-gemini")
async def delete_gemini_credential(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Permanently delete the encrypted Gemini BYOK key for this workspace.
    Resets provider mode to HELIX Managed.
    """
    org = await get_or_create_default_org(db, user)
    stmt = delete(WorkspaceProviderCredential).where(
        WorkspaceProviderCredential.org_id == org.id,
        WorkspaceProviderCredential.provider == "google_gemini"
    )
    await db.execute(stmt)
    await db.commit()

    return {
        "status": "deleted",
        "provider": "google_gemini",
        "credential_mode": "managed",
        "message": "Gemini BYOK key removed. Workspace restored to HELIX Managed provider."
    }

@router.post("/workspaces/provider-mode")
async def set_workspace_provider_mode(
    body: SetProviderModeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Toggle active provider mode between 'managed' and 'byok'.
    """
    if body.credential_mode not in ("managed", "byok"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credential_mode. Must be 'managed' or 'byok'"
        )

    org = await get_or_create_default_org(db, user)
    stmt = select(WorkspaceProviderCredential).where(
        WorkspaceProviderCredential.org_id == org.id,
        WorkspaceProviderCredential.provider == "google_gemini"
    )
    result = await db.execute(stmt)
    cred = result.scalar_one_or_none()

    if body.credential_mode == "byok" and (not cred or not cred.encrypted_secret):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot select BYOK mode without a connected Gemini API key"
        )

    if cred:
        cred.credential_mode = body.credential_mode
        await db.commit()

    return {
        "status": "updated",
        "provider": "google_gemini",
        "credential_mode": body.credential_mode
    }
