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


# --- SSRF Protection ---

import ipaddress
import socket
from urllib.parse import urlparse

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
]

BLOCKED_HOSTNAMES = {"localhost", "metadata", "instance-data"}


def is_safe_public_url(url: str) -> bool:
    """
    Validates that a URL is a legitimate public web destination.
    Rejects private IPs, loopback, AWS/GCP/Azure metadata services, and internal hostnames.
    Prevents Server-Side Request Forgery (SSRF).
    """
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme.lower() not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        hostname_lower = hostname.lower().strip(".")
        if hostname_lower in BLOCKED_HOSTNAMES or hostname_lower.endswith(".local") or hostname_lower.endswith(".internal"):
            return False

        # If hostname is direct IP literal
        try:
            ip = ipaddress.ip_address(hostname_lower)
            return not any(ip in net for net in BLOCKED_NETWORKS)
        except ValueError:
            pass

        # Resolve DNS to check resulting IPs
        addr_info = socket.getaddrinfo(hostname_lower, None)
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
                if any(ip in net for net in BLOCKED_NETWORKS):
                    return False
            except ValueError:
                return False
        return True
    except Exception:
        return False

