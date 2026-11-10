"""Drop secret-looking fields from payloads before they are stored or returned.

Moved here from app/schemas/media.py when Create (media generation) was
removed; playbooks still use it for user-supplied pattern payloads.
"""
from typing import Any

_SECRET_EXACT = {
    "custom_api_key",
    "api_key",
    "apikey",
    "api_secret",
    "secret",
    "password",
    "access_token",
    "refresh_token",
    "id_token",
    "token",
    "authorization",
    "cookie",
    "hunter_api_key",
    "linkedin_cookie",
    "linkedin_byok_cookie",
    "private_key",
    "client_secret",
}


def is_secret_field(name: str) -> bool:
    lowered = str(name or "").lower().replace("-", "_")
    if lowered in _SECRET_EXACT:
        return True
    return (
        lowered.endswith("_api_key")
        or lowered.endswith("_secret")
        or lowered.endswith("_token")
        or lowered.endswith("_password")
        or "api_key" in lowered
    )


def strip_secret_fields(value: Any) -> Any:
    """Drop secret fields from a payload, including nested objects and lists."""
    if isinstance(value, dict):
        return {key: strip_secret_fields(item) for key, item in value.items() if not is_secret_field(key)}
    if isinstance(value, list):
        return [strip_secret_fields(item) for item in value]
    return value
