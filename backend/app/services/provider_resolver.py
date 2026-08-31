"""
Provider Resolver Layer for Helix Intelligence Media Generation.

Determines whether to use HELIX Managed Gemini or Workspace BYOK (Bring Your Own Key)
based on workspace subscription tier, settings, and entitlement rules.
"""

import logging
from typing import Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User
from app.models.organization import Organization
from app.models.workspace_credential import WorkspaceProviderCredential
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.pollinations_provider import PollinationsProvider
from app.services.security_service import decrypt_secret
from app.services.billing_service import is_trial_active

logger = logging.getLogger(__name__)

async def resolve_image_provider(
    db: AsyncSession,
    user: User,
    org: Organization
) -> Tuple[Any, str]:
    """
    Resolves the appropriate GeminiProvider instance and credential mode.
    Returns:
        (provider_instance, credential_mode) where credential_mode in ('managed', 'byok')
    
    Rules:
      - Trial accounts ALWAYS use HELIX Managed Gemini (managed).
      - Paid workspaces / Admins may use BYOK if explicitly configured and selected.
      - If BYOK is active, returns GeminiProvider initialized with the decrypted workspace key.
    """
    is_trial = is_trial_active(user) and (org.plan == "trial" or bool(org.plan_id and org.plan_id.startswith("plan_trial")))
    is_admin = getattr(user, "role", "") == "admin"

    # Trial accounts always use managed provider
    if is_trial and not is_admin:
        return PollinationsProvider(), "managed"

    # Query workspace provider credential
    stmt = select(WorkspaceProviderCredential).where(
        WorkspaceProviderCredential.org_id == org.id,
        WorkspaceProviderCredential.provider == "google_gemini"
    )
    result = await db.execute(stmt)
    credential = result.scalar_one_or_none()

    if credential and credential.credential_mode == "byok" and credential.encrypted_secret:
        try:
            plaintext_key = decrypt_secret(credential.encrypted_secret)
            if plaintext_key:
                return GeminiProvider(api_key=plaintext_key), "byok"
        except Exception as e:
            logger.error("Failed to decrypt workspace Gemini BYOK key for org %s: %s", org.id, e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "byok_decryption_failed",
                    "message": "Failed to decrypt your connected Gemini API key. Please reconnect your key in workspace settings."
                }
            )

    # Default to HELIX Managed Provider (now Pollinations instead of Gemini to avoid quota)
    return PollinationsProvider(), "managed"
