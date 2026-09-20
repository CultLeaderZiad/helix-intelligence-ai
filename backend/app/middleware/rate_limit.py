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

import time
import logging
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
    ]


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # (bucket_key) -> deque[timestamps]
        self._buckets: Dict[str, Deque[float]] = defaultdict(deque)

    def _client_ip(self, request: Request) -> str:
        # Render/Cloudflare set X-Forwarded-For; take the left-most (original) hop.
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        path = request.url.path
        rule = next((r for r in _rules() if path.startswith(r[0])), None)
        if rule is None:
            return await call_next(request)

        prefix, limit, window = rule
        # Only rate-limit state-changing methods on these endpoints.
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return await call_next(request)

        try:
            key = f"{prefix}:{self._client_ip(request)}"
            now = time.monotonic()
            bucket = self._buckets[key]

            # Drop timestamps outside the current window.
            while bucket and now - bucket[0] > window:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after = int(window - (now - bucket[0])) + 1 if bucket else window
                logger.warning("Rate limit hit: %s from %s", prefix, self._client_ip(request))
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
        except Exception as exc:  # fail open — never let the shield break the app
            logger.error("Rate limiter error (failing open): %s", exc)

        return await call_next(request)
