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

from app.core.config import settings

logger = logging.getLogger(__name__)

# path-prefix -> (max_requests, window_seconds). First match wins, so list the
# most specific prefixes first.
def _rules() -> list[Tuple[str, int, int]]:
    return [
        ("/api/auth/sign-in", settings.AUTH_RATE_LIMIT, settings.AUTH_RATE_LIMIT_WINDOW_S),
        ("/api/auth/sign-up", settings.AUTH_RATE_LIMIT, settings.AUTH_RATE_LIMIT_WINDOW_S),
        ("/api/auth/forgot-password", settings.AUTH_RATE_LIMIT, settings.AUTH_RATE_LIMIT_WINDOW_S),
        ("/api/auth/reset-password", settings.AUTH_RATE_LIMIT, settings.AUTH_RATE_LIMIT_WINDOW_S),
        ("/api/discovery/jobs", settings.EXPENSIVE_RATE_LIMIT, settings.EXPENSIVE_RATE_LIMIT_WINDOW_S),
        ("/api/media/jobs", settings.EXPENSIVE_RATE_LIMIT, settings.EXPENSIVE_RATE_LIMIT_WINDOW_S),
        ("/api/scout/jobs", settings.EXPENSIVE_RATE_LIMIT, settings.EXPENSIVE_RATE_LIMIT_WINDOW_S),
        ("/api/scout/maps/jobs", settings.EXPENSIVE_RATE_LIMIT, settings.EXPENSIVE_RATE_LIMIT_WINDOW_S),
        ("/api/leadgen/jobs", settings.EXPENSIVE_RATE_LIMIT, settings.EXPENSIVE_RATE_LIMIT_WINDOW_S),
    ]


def _is_valid_public_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return not (ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local or ip.is_multicast or ip.is_unspecified)
    except ValueError:
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # (bucket_key) -> deque[timestamps]
        self._buckets: Dict[str, Deque[float]] = defaultdict(deque)

    def _client_ip(self, request: Request) -> str:
        # 1. Cloudflare single-hop client IP
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip and cf_ip.strip():
            return cf_ip.strip()

        # 2. Akamai / Cloudflare enterprise True-Client-IP
        true_ip = request.headers.get("true-client-ip")
        if true_ip and true_ip.strip():
            return true_ip.strip()

        # 3. X-Forwarded-For: reverse-traverse to find the rightmost non-private/valid public IP
        # to prevent client spoofing via prepended header values.
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            hops = [h.strip() for h in fwd.split(",") if h.strip()]
            for hop in reversed(hops):
                if _is_valid_public_ip(hop):
                    return hop
            if hops:
                return hops[-1]

        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Normalize /api/v1/ prefix aliases to /api/
        path = request.url.path
        normalized_path = re.sub(r"^/api/v1/", "/api/", path)
        rule = next((r for r in _rules() if normalized_path.startswith(r[0])), None)
        if rule is None:
            return await call_next(request)

        prefix, limit, window = rule
        # Only rate-limit state-changing methods on these endpoints.
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return await call_next(request)

        try:
            client_ip = self._client_ip(request)
            key = f"{prefix}:{client_ip}"
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

        except Exception as exc:  # fail open — never let the shield break the app
            logger.error("Rate limiter error (failing open): %s", exc)

        return await call_next(request)
