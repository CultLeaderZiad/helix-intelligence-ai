"""Temporary: show which forwarding headers Render delivers, to pick the one
that carries the real client IP.

Only requests to ``/api/health`` with a ``probe`` query parameter are logged,
so normal traffic is never recorded. Every IP address is masked to its first
two parts (``197.37.x.x``), enough to tell the real address from a forged one
and the order of entries, never a full address. Remove once the header is
chosen (see docs/SECURITY_AUDIT.md, A1).
"""
from __future__ import annotations

import ipaddress
import logging
import re

logger = logging.getLogger("helix.forwarding_probe")

HEADERS = (
    "x-forwarded-for",
    "x-real-ip",
    "true-client-ip",
    "cf-connecting-ip",
    "forwarded",
    "x-forwarded-proto",
    "cf-ray",
    "rndr-id",
)
_PROBE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def mask(value: str) -> str:
    """Mask every IP-looking token in a header value."""

    def _one(token: str) -> str:
        bare = token.strip().strip('"').strip("[]")
        try:
            ip = ipaddress.ip_address(bare)
        except ValueError:
            return token
        if ip.version == 4:
            a, b, _c, _d = bare.split(".")
            return f"{a}.{b}.x.x"
        return ":".join(bare.split(":")[:2]) + ":x"

    return re.sub(r"[0-9A-Fa-f:.\[\]]{7,}", lambda m: _one(m.group(0)), value)[:300]


def describe(path: str, query: str, headers, peer: str | None) -> str | None:
    """The log line for a probe request, or None for any other request."""
    if path.rstrip("/") != "/api/health":
        return None
    match = re.search(r"(?:^|&)probe=([^&]*)", query or "")
    if not match or not _PROBE.match(match.group(1)):
        return None
    seen = {name: mask(headers.get(name)) for name in HEADERS if headers.get(name)}
    return f"forwarding probe={match.group(1)} peer={mask(peer or '-')} headers={seen}"


async def log_probe(request, call_next):
    try:
        line = describe(request.url.path, request.url.query, request.headers,
                        request.client.host if request.client else None)
        if line:
            logger.warning(line)
    except Exception:  # diagnostics must never break a request
        pass
    return await call_next(request)
