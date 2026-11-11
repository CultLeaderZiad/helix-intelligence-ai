"""In-memory, per-process rate limiting middleware.

Protects the two classes of endpoint that cost real money or security when
abused:

* **Credential endpoints** (`/api/auth/sign-in`, `/sign-up`, `/forgot-password`,
  `/reset-password`) — brute-force and account-enumeration targets.
* **Expensive AI / scrape endpoints** (`/api/discovery/jobs`, `/api/media/jobs`)
  — each call burns provider credits; a burst can drain the org ledger.

Design notes
------------
This is a fixed-window token bucket keyed by client IP, held in process
memory. On Helix's single Render web instance that is exactly right: no Redis,
no extra service, zero latency added to the hot path. It is **per-process**,
so if the app ever scales horizontally the effective limit becomes
`limit × instance_count` — acceptable for now and documented as such.

Fail-open vs fail-closed: on any internal error the middleware **fails open**
(lets the request through) rather than take the API down with a bug in the
limiter itself. The limiter is a shield, not a single point of failure.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import effective_trusted_proxy_cidrs, settings

logger = logging.getLogger(__name__)

# Paid AI routes share one bucket so a caller cannot rotate paths to multiply
# the budget. Auth routes keep their own buckets.
PAID_AI_BUCKET = "paid-ai"


WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
ANY_METHOD = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE")


def _rules() -> list[Tuple[str, int, int, str, tuple]]:
    """(path prefix, limit, window seconds, bucket, methods). First match wins."""
    auth_limit = settings.AUTH_RATE_LIMIT
    auth_window = settings.AUTH_RATE_LIMIT_WINDOW_S
    paid_limit = settings.EXPENSIVE_RATE_LIMIT
    paid_window = settings.EXPENSIVE_RATE_LIMIT_WINDOW_S
    abuse_limit = settings.ABUSE_RATE_LIMIT
    abuse_window = settings.ABUSE_RATE_LIMIT_WINDOW_S
    return [
        ("/api/auth/sign-in", auth_limit, auth_window, "auth-sign-in", WRITE_METHODS),
        ("/api/auth/sign-up", auth_limit, auth_window, "auth-sign-up", WRITE_METHODS),
        ("/api/auth/forgot-password", auth_limit, auth_window, "auth-forgot", WRITE_METHODS),
        ("/api/auth/reset-password", auth_limit, auth_window, "auth-reset", WRITE_METHODS),
        ("/api/discovery/jobs", paid_limit, paid_window, PAID_AI_BUCKET, WRITE_METHODS),
        ("/api/creatives/", paid_limit, paid_window, PAID_AI_BUCKET, WRITE_METHODS),
        ("/api/playbooks", paid_limit, paid_window, PAID_AI_BUCKET, WRITE_METHODS),
        # Monitor runs spend provider records like a search does.
        ("/api/monitors", paid_limit, paid_window, PAID_AI_BUCKET, WRITE_METHODS),
        # Writes that send email or create rows other people see.
        ("/api/support/tickets", abuse_limit, abuse_window, "support", WRITE_METHODS),
        ("/api/account/access-requests", abuse_limit, abuse_window, "access-request", WRITE_METHODS),
        ("/api/boards/share-links", abuse_limit, abuse_window, "share-links", WRITE_METHODS),
        ("/api/discovery/drafts", abuse_limit, abuse_window, "drafts", WRITE_METHODS),
        # Unauthenticated token lookups: slow down guessing.
        ("/api/public/boards", auth_limit, auth_window, "guest-board", ANY_METHOD),
    ]


def _trusted_networks():
    networks = []
    raw = effective_trusted_proxy_cidrs(settings)
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        if "/" not in item:
            ip = ipaddress.ip_address(item)
            item = f"{item}/32" if ip.version == 4 else f"{item}/128"
        networks.append(ipaddress.ip_network(item, strict=False))
    return networks


def _is_valid_public_ip(ip_str: str) -> bool:
    """True for a globally routable address. Not used to trust forwarding headers."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_reserved
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
    )


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _is_trusted_proxy(value: str) -> bool:
    if not _is_ip(value):
        return False
    ip = ipaddress.ip_address(value)
    return any(ip in network for network in _trusted_networks())


_proxy_warning_logged = False


def warn_if_untrusted_proxy(request: Request) -> bool:
    """Log once when a private peer forwards client IPs we are told not to trust.

    Behind a hosting proxy (Render, a load balancer) every client then shares
    the proxy's address, so one IP bucket covers all users. Returns True when
    the warning applies (for tests); never raises.
    """
    global _proxy_warning_logged
    peer = request.client.host if request.client and request.client.host else ""
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("cf-connecting-ip")
    if not peer or not forwarded or not _is_ip(peer) or _is_trusted_proxy(peer):
        return False
    if _is_valid_public_ip(peer):
        return False
    if not _proxy_warning_logged:
        _proxy_warning_logged = True
        logger.warning(
            "Rate limiting keys on proxy address %s: forwarding headers are present but "
            "TRUSTED_PROXY_CIDRS does not include it, so all clients share one bucket. "
            "Add the proxy range to TRUSTED_PROXY_CIDRS.",
            peer,
        )
    return True


def client_ip(request: Request) -> str:
    """Return the client IP from the TCP peer unless that peer is a trusted proxy."""
    peer = request.client.host if request.client and request.client.host else ""
    if not peer:
        return "unknown"
    if not _is_trusted_proxy(peer):
        return peer
    for header_name in ("cf-connecting-ip", "true-client-ip"):
        forwarded = (request.headers.get(header_name) or "").strip()
        if forwarded and _is_ip(forwarded) and not _is_trusted_proxy(forwarded):
            return forwarded
    hops = [hop.strip() for hop in (request.headers.get("x-forwarded-for") or "").split(",") if hop.strip()]
    for hop in reversed(hops):
        if _is_ip(hop) and not _is_trusted_proxy(hop):
            return hop
    return peer


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # (bucket_key) -> deque[timestamps]
        self._buckets: Dict[str, Deque[float]] = defaultdict(deque)

    def _client_ip(self, request: Request) -> str:
        return client_ip(request)

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Normalize /api/v1/ prefix aliases to /api/
        path = request.url.path
        normalized_path = re.sub(r"^/api/v1/", "/api/", path)
        rule = next((r for r in _rules() if normalized_path.startswith(r[0])), None)
        if rule is None:
            return await call_next(request)

        prefix, limit, window, bucket, methods = rule
        if request.method not in methods:
            return await call_next(request)

        try:
            warn_if_untrusted_proxy(request)
            client_ip = self._client_ip(request)
            key = f"{bucket}:{client_ip}"
            now = time.monotonic()
            bucket = self._buckets[key]

            # Drop timestamps outside the current window.
            while bucket and now - bucket[0] > window:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after = int(window - (now - bucket[0])) + 1 if bucket else window
                logger.warning("Rate limit hit: %s from %s", prefix, client_ip)
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": {
                            "code": "rate_limited",
                            "message": "Too many requests. Please slow down and try again shortly.",
                        }
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            bucket.append(now)

            # Evict empty/expired keys if table grows large to avoid unbounded memory leaks
            if len(self._buckets) > 500:
                stale_keys = [
                    k for k, deq in self._buckets.items()
                    if not deq or (now - deq[-1] > 3600)
                ]
                for k in stale_keys:
                    self._buckets.pop(k, None)

        except Exception as exc:
            # Credential endpoints fail closed: an unthrottled sign-in is a
            # brute-force window. Everything else fails open so a limiter bug
            # cannot take the product down.
            if prefix.startswith("/api/auth/"):
                logger.error("Rate limiter error on %s (failing closed): %s", prefix, exc)
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": {
                            "code": "auth_rate_limiter_unavailable",
                            "message": "Sign-in is briefly unavailable. Please try again shortly.",
                        }
                    },
                    headers={"Retry-After": "5"},
                )
            logger.error("Rate limiter error (failing open): %s", exc)

        return await call_next(request)
