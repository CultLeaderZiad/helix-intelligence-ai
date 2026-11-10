"""
Server-side encryption for BYOK credentials.

Ciphertexts are versioned Fernet tokens derived from CREDENTIAL_ENCRYPTION_KEY.
That key is separate from the JWT signing secret. Plaintext and signing-key
fallbacks are not accepted.
"""

import base64
import hashlib
import logging
import os
import secrets
import threading
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import classified_environment, settings

logger = logging.getLogger(__name__)

_ephemeral_lock = threading.Lock()
_ephemeral_key: Optional[str] = None


def _ephemeral_material() -> str:
    """Process-local key used only outside production when no key is configured."""
    global _ephemeral_key
    with _ephemeral_lock:
        if _ephemeral_key is None:
            _ephemeral_key = secrets.token_urlsafe(32)
            logger.warning(
                "CREDENTIAL_ENCRYPTION_KEY is unset; using a process-local key. "
                "Set CREDENTIAL_ENCRYPTION_KEY before storing credentials that must survive a restart."
            )
        return _ephemeral_key


def _fernet_from_material(material: str) -> Fernet:
    raw = (material or "").strip()
    if not raw:
        raise RuntimeError("Missing required integration key: CREDENTIAL_ENCRYPTION_KEY")
    try:
        decoded = base64.urlsafe_b64decode(raw.encode("utf-8"))
        if len(decoded) == 32:
            key = raw.encode("utf-8") if len(raw) == 44 else base64.urlsafe_b64encode(decoded)
            return Fernet(key)
    except Exception:
        pass
    derived = base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest())
    return Fernet(derived)


def _key_material(version: Optional[int] = None) -> tuple[int, str]:
    current = int(getattr(settings, "CREDENTIAL_ENCRYPTION_KEY_VERSION", 1) or 1)
    current_key = (getattr(settings, "CREDENTIAL_ENCRYPTION_KEY", "") or "").strip()
    previous = (getattr(settings, "CREDENTIAL_ENCRYPTION_KEY_PREVIOUS", "") or "").strip()
    if current_key and current_key == (settings.SECRET_KEY or ""):
        raise RuntimeError("CREDENTIAL_ENCRYPTION_KEY must not equal SECRET_KEY")
    target = current if version is None else version
    if target == current:
        if current_key:
            return target, current_key
        if classified_environment(settings) == "production" or os.getenv("RENDER"):
            raise RuntimeError("Missing required integration key: CREDENTIAL_ENCRYPTION_KEY")
        return target, _ephemeral_material()
    if previous and target == current - 1:
        return target, previous
    raise ValueError("Unknown credential encryption key version")


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret as ``v<version>:<fernet>`` using the current encryption key."""
    if not plaintext:
        return ""
    version, material = _key_material()
    token = _fernet_from_material(material).encrypt(plaintext.strip().encode("utf-8"))
    return f"v{version}:{token.decode('utf-8')}"


def decrypt_secret(encrypted_token: str) -> str:
    """Decrypt a versioned Fernet token. Unversioned or foreign values raise."""
    if not encrypted_token:
        return ""
    token = encrypted_token.strip()
    if not token.startswith("v") or ":" not in token:
        raise ValueError("Ciphertext is not a versioned credential")
    version_text, fernet_token = token.split(":", 1)
    try:
        version = int(version_text[1:])
    except ValueError as exc:
        raise ValueError("Ciphertext is not a versioned credential") from exc
    _version, material = _key_material(version)
    try:
        decrypted = _fernet_from_material(material).decrypt(fernet_token.encode("utf-8"))
    except InvalidToken as exc:
        raise ValueError("Credential ciphertext could not be decrypted") from exc
    return decrypted.decode("utf-8")


def safe_decrypt_secret(value: Optional[str]) -> str:
    """Decrypt a versioned secret. Returns an empty string instead of plaintext."""
    if not value:
        return ""
    try:
        return decrypt_secret(value)
    except Exception:
        logger.warning("Rejected a credential value that is not a versioned ciphertext")
        return ""

def mask_api_key(key: str) -> str:
    """Mask an API key for safe display (e.g. ••••••••abcd)."""
    if not key:
        return ""
    clean = key.strip()
    if len(clean) <= 6:
        return "••••••••"
    return f"••••••••{clean[-4:]}"


# --- SSRF Protection ---

import ipaddress

BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),       # Cloud IMDS (169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("::ffff:0:0/96"),
]

BLOCKED_HOSTNAMES = {"localhost", "metadata", "instance-data", "metadata.google.internal"}


def is_ip_blocked(ip: ipaddress._BaseAddress) -> bool:
    """Check if an IPv4 or IPv6 address is private, loopback, link-local, or in blocked networks."""
    # If IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1), unmap to check underlying IPv4
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped

    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return True

    for net in BLOCKED_NETWORKS:
        if net.version == ip.version and ip in net:
            return True

    return False


def is_safe_public_url(url: str) -> bool:
    """True when ``url`` passes the shared public-fetch policy, including DNS."""
    try:
        from app.services.safe_fetch import assert_public_http_url
        assert_public_http_url(url)
        return True
    except Exception:
        return False


def safe_http_get(url: str, timeout: float = 20.0, max_redirects: int = 5, **kwargs):
    """GET a public URL, pinning the connection and rechecking every redirect."""
    from app.services.safe_fetch import safe_http_get as _safe_http_get
    return _safe_http_get(url, timeout=timeout, max_redirects=max_redirects, **kwargs)


