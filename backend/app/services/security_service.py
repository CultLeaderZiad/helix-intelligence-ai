"""
Server-side Encryption and Secrets Management Service for BYOK credentials.
Ensures customer API keys are encrypted at rest using server environment SECRET_KEY.
Keys are NEVER logged, NEVER returned in plaintext in API responses, and NEVER exposed to clients.
"""

import base64
import hashlib
import logging
from typing import Optional
from cryptography.fernet import Fernet
from app.core.config import settings

logger = logging.getLogger(__name__)

def _get_fernet_cipher() -> Fernet:
    """Derive a deterministic 32-byte urlsafe base64 key from settings.SECRET_KEY."""
    raw_key = settings.SECRET_KEY or "helix-default-dev-secret-key-32bytes!!"
    # Use SHA-256 to ensure a 32-byte key
    derived_bytes = hashlib.sha256(raw_key.encode("utf-8")).digest()
    urlsafe_key = base64.urlsafe_b64encode(derived_bytes)
    return Fernet(urlsafe_key)

def encrypt_secret(plaintext: str) -> str:
    """Encrypt a plaintext secret (e.g. BYOK API key) into a Fernet token string."""
    if not plaintext:
        return ""
    cipher = _get_fernet_cipher()
    encrypted_bytes = cipher.encrypt(plaintext.strip().encode("utf-8"))
    return encrypted_bytes.decode("utf-8")

def decrypt_secret(encrypted_token: str) -> str:
    """Decrypt a Fernet token string back into plaintext secret."""
    if not encrypted_token:
        return ""
    cipher = _get_fernet_cipher()
    decrypted_bytes = cipher.decrypt(encrypted_token.strip().encode("utf-8"))
    return decrypted_bytes.decode("utf-8")

def mask_api_key(key: str) -> str:
    """Mask an API key for safe display (e.g. ••••••••abcd)."""
    if not key:
        return ""
    clean = key.strip()
    if len(clean) <= 6:
        return "••••••••"
    return f"••••••••{clean[-4:]}"
