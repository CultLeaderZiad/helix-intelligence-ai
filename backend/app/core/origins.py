"""Validation helpers for configured network targets."""

from ipaddress import ip_address
from urllib.parse import SplitResult, urlsplit


_HTTP_SCHEMES = frozenset({"http", "https"})
_DATABASE_SCHEMES = frozenset(
    {
        "postgres",
        "postgresql",
        "postgresql+asyncpg",
        "postgresql+psycopg",
        "sqlite",
        "sqlite+aiosqlite",
    }
)


def is_loopback_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    host = hostname.strip().lower().strip("[]").rstrip(".")
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def validate_http_target(
    value: str | None,
    *,
    name: str,
    environment: str,
    allow_relative: bool = False,
    origin_only: bool = False,
) -> SplitResult | None:
    """Require loopback URLs outside production and HTTPS URLs in production."""
    raw = (value or "").strip()
    if not raw:
        return None

    if raw.startswith("/"):
        if not allow_relative or raw.startswith("//") or "\\" in raw:
            raise ValueError(f"{name} must be an absolute HTTP(S) URL")
        relative = urlsplit(raw)
        if relative.netloc or relative.query or relative.fragment:
            raise ValueError(f"{name} must not contain a query or fragment")
        return None

    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError:
        raise ValueError(f"{name} must be a valid HTTP(S) URL") from None
    if parsed.scheme.lower() not in _HTTP_SCHEMES or not parsed.hostname:
        raise ValueError(f"{name} must be a valid HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{name} must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{name} must not contain a query or fragment")
    if origin_only and parsed.path not in ("", "/"):
        raise ValueError(f"{name} must contain origins only")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError(f"{name} must use a valid port")

    loopback = is_loopback_host(parsed.hostname)
    if environment != "production" and not loopback:
        raise ValueError(f"{name} must use a loopback host outside production")
    if environment == "production" and (loopback or parsed.scheme.lower() != "https"):
        raise ValueError(f"{name} must use a public HTTPS host in production")
    return parsed


def validate_database_target(value: str | None, *, environment: str) -> None:
    raw = (value or "").strip()
    if not raw:
        return
    try:
        parsed = urlsplit(raw)
    except ValueError:
        raise ValueError("DATABASE_URL must be a valid database URL") from None
    if parsed.scheme.lower() not in _DATABASE_SCHEMES:
        raise ValueError("DATABASE_URL must use a supported database scheme")
    if environment != "production" and parsed.hostname and not is_loopback_host(parsed.hostname):
        raise ValueError("DATABASE_URL must use a loopback host outside production")
