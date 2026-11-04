"""Validation helpers for configured network targets."""

from ipaddress import ip_address
import re
from urllib.parse import SplitResult, parse_qs, urlsplit


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
_HOST_LABEL = re.compile(r"^[A-Za-z0-9-]+$")


def _valid_hostname(hostname: str) -> bool:
    host = hostname.rstrip(".")
    if not host or any(char.isspace() or char in "/\\?#@[]" for char in host):
        return False
    try:
        ip_address(host)
        return True
    except ValueError:
        pass
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return False
    labels = ascii_host.split(".")
    return len(ascii_host) <= 253 and all(
        0 < len(label) <= 63
        and _HOST_LABEL.fullmatch(label)
        and not label.startswith("-")
        and not label.endswith("-")
        for label in labels
    )


def is_loopback_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    host = hostname.strip().lower().strip("[]").rstrip(".")
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        address = ip_address(host)
        if address.version == 6 and address.ipv4_mapped:
            return address.ipv4_mapped.is_loopback
        return address.is_loopback
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
        if "\\" in raw:
            raise ValueError
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError:
        raise ValueError(f"{name} must be a valid HTTP(S) URL") from None
    if (
        parsed.scheme.lower() not in _HTTP_SCHEMES
        or not parsed.hostname
        or not _valid_hostname(parsed.hostname)
    ):
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
    dns_host = re.search(r"\.[A-Za-z][A-Za-z0-9-]*$", parsed.hostname.rstrip(".").encode("idna").decode("ascii"))
    if environment == "production" and (loopback or not dns_host or parsed.scheme.lower() != "https"):
        raise ValueError(f"{name} must use a public HTTPS DNS host in production")
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
    if parsed.hostname and not _valid_hostname(parsed.hostname):
        raise ValueError("DATABASE_URL must contain a valid host")
    if environment != "production":
        if parsed.hostname and not is_loopback_host(parsed.hostname):
            raise ValueError("DATABASE_URL must use a loopback host outside production")
        query = parse_qs(parsed.query, keep_blank_values=True)
        overrides = query.get("host", []) + query.get("hostaddr", [])
        if any(not (host.startswith("/") or is_loopback_host(host)) for host in overrides):
            raise ValueError("DATABASE_URL host overrides must use loopback hosts or local sockets")
        if parsed.scheme.startswith("postgres") and not parsed.hostname and not overrides:
            raise ValueError("DATABASE_URL must explicitly select a loopback host or local socket")
